"""
SwissBuildingOS - Building Health Index Service

Computes a composite 0-100 health score for a building across five dimensions:
  - Pollutant status (30%)
  - Structural condition (20%)
  - Compliance (20%)
  - Documentation completeness (15%)
  - Monitoring compliance (15%)

Provides breakdown, trajectory projection, and portfolio-level dashboard.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone
from app.schemas.building_health_index import (
    BuildingHealthSummary,
    DimensionScore,
    HealthBreakdown,
    HealthIndex,
    HealthTrajectory,
    ImprovementLever,
    PortfolioHealthDashboard,
    RecommendedAction,
    TrajectoryPoint,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS = {
    "pollutant_status": 0.30,
    "structural_condition": 0.20,
    "compliance": 0.20,
    "documentation_completeness": 0.15,
    "monitoring_compliance": 0.15,
}

GRADE_THRESHOLDS = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (20, "E"),
    (0, "F"),
]

_ALL_POLLUTANTS_SET: set[str] = set(ALL_POLLUTANTS)

# Monthly decay rate when no action is taken (score points per month)
DECAY_RATE_PER_MONTH = 1.5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_to_grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------


def _score_pollutant_status(
    samples: list[Sample],
    diagnostics: list[Diagnostic],
) -> tuple[float, list[str]]:
    """Score pollutant status dimension (0-100).

    High score = few/no pollutants found or all addressed.
    """
    factors: list[str] = []

    if not diagnostics:
        factors.append("No diagnostics performed")
        return 20.0, factors

    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    if not completed_diags:
        factors.append("No completed diagnostics")
        return 30.0, factors

    if not samples:
        factors.append("No samples taken")
        return 50.0, factors

    total = len(samples)
    exceeded = [s for s in samples if s.threshold_exceeded]
    exceeded_count = len(exceeded)

    # Base score: ratio of clean samples
    clean_ratio = (total - exceeded_count) / total if total > 0 else 1.0
    score = clean_ratio * 70 + 30  # Range: 30-100

    # Check pollutant coverage
    evaluated = {(s.pollutant_type or "").lower() for s in samples} & _ALL_POLLUTANTS_SET
    missing = _ALL_POLLUTANTS_SET - evaluated
    if missing:
        coverage_penalty = len(missing) * 5
        score = max(10, score - coverage_penalty)
        factors.append(f"Missing evaluation: {', '.join(sorted(missing))}")

    if exceeded_count > 0:
        factors.append(f"{exceeded_count}/{total} samples exceed thresholds")
        # Check risk levels of exceeded samples
        critical = [s for s in exceeded if s.risk_level in ("high", "critical")]
        if critical:
            factors.append(f"{len(critical)} high/critical risk sample(s)")
            score = max(10, score - len(critical) * 5)
    else:
        factors.append("All samples within thresholds")

    return round(min(100, max(0, score)), 1), factors


def _score_structural_condition(
    elements: list[BuildingElement],
    building: Building,
) -> tuple[float, list[str]]:
    """Score structural condition dimension (0-100).

    Based on building element conditions and age.
    """
    factors: list[str] = []

    if not elements:
        # Fall back to age-based estimate
        year = building.construction_year
        if year is None:
            factors.append("No structural data or construction year")
            return 50.0, factors
        age = datetime.now(UTC).year - year
        if age <= 10:
            score = 90.0
        elif age <= 30:
            score = 75.0
        elif age <= 50:
            score = 55.0
        else:
            score = 35.0
        factors.append(f"Estimated from building age ({age} years)")
        return score, factors

    condition_scores = {
        "excellent": 100,
        "good": 80,
        "fair": 60,
        "poor": 35,
        "critical": 10,
    }

    scored = []
    for el in elements:
        cond = (el.condition or "").lower()
        if cond in condition_scores:
            scored.append(condition_scores[cond])

    if not scored:
        factors.append("No condition data on elements")
        return 50.0, factors

    avg = sum(scored) / len(scored)
    worst = min(scored)
    if worst <= 10:
        factors.append("Critical condition element(s) detected")
    elif worst <= 35:
        factors.append("Poor condition element(s) detected")

    factors.append(f"{len(scored)} elements assessed")
    return round(avg, 1), factors


def _score_compliance(
    samples: list[Sample],
    diagnostics: list[Diagnostic],
    actions: list[ActionItem],
) -> tuple[float, list[str]]:
    """Score compliance dimension (0-100).

    Checks regulatory compliance: SUVA notifications, work categories,
    waste classification, action status.
    """
    factors: list[str] = []
    sub_scores: list[float] = []

    # SUVA notification compliance
    positive_asbestos = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
    if positive_asbestos:
        notified = any(d.suva_notification_required and d.suva_notification_date for d in diagnostics)
        if notified:
            sub_scores.append(100)
        else:
            sub_scores.append(0)
            factors.append("SUVA notification missing for positive asbestos")
    else:
        sub_scores.append(100)  # Not applicable = full score

    # Work category assignment
    asbestos_needing_category = [s for s in positive_asbestos if not s.cfst_work_category]
    if positive_asbestos:
        ratio = 1 - (len(asbestos_needing_category) / len(positive_asbestos))
        sub_scores.append(ratio * 100)
        if asbestos_needing_category:
            factors.append(f"{len(asbestos_needing_category)} asbestos sample(s) missing work category")
    else:
        sub_scores.append(100)

    # Waste classification
    positive_samples = [s for s in samples if s.threshold_exceeded]
    if positive_samples:
        unclassified = [s for s in positive_samples if not s.waste_disposal_type]
        ratio = 1 - (len(unclassified) / len(positive_samples))
        sub_scores.append(ratio * 100)
        if unclassified:
            factors.append(f"{len(unclassified)} positive sample(s) missing waste classification")
    else:
        sub_scores.append(100)

    # Critical actions
    critical_open = [a for a in actions if a.status == "open" and a.priority in ("critical", "high")]
    if critical_open:
        sub_scores.append(max(0, 100 - len(critical_open) * 20))
        factors.append(f"{len(critical_open)} open critical/high action(s)")
    else:
        sub_scores.append(100)

    if not factors:
        factors.append("All compliance requirements met")

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 50.0
    return round(min(100, max(0, score)), 1), factors


def _score_documentation_completeness(
    diagnostics: list[Diagnostic],
    documents: list[Document],
    plans: list[TechnicalPlan],
    samples: list[Sample],
) -> tuple[float, list[str]]:
    """Score documentation completeness dimension (0-100).

    Checks presence of reports, lab reports, plans.
    """
    factors: list[str] = []
    checks_passed = 0
    checks_total = 0

    # Has diagnostic report
    checks_total += 1
    reports = [d for d in documents if (d.document_type or "").lower() in ("diagnostic_report", "report")]
    if reports:
        checks_passed += 1
    else:
        factors.append("No diagnostic report uploaded")

    # Has lab reports
    pollutants_with_samples = {(s.pollutant_type or "").lower() for s in samples} & _ALL_POLLUTANTS_SET
    if pollutants_with_samples:
        checks_total += 1
        lab_reports = [d for d in documents if (d.document_type or "").lower() in ("lab_report", "lab_analysis")]
        if lab_reports:
            checks_passed += 1
        else:
            factors.append("No lab analysis reports")

    # Has floor plans
    checks_total += 1
    floor_plans = [p for p in plans if (p.plan_type or "").lower() == "floor_plan"]
    if floor_plans:
        checks_passed += 1
    else:
        factors.append("No floor plans uploaded")

    # Has completed diagnostic
    checks_total += 1
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed:
        checks_passed += 1
    else:
        factors.append("No completed diagnostic")

    # All samples have lab results
    if samples:
        checks_total += 1
        missing_results = [s for s in samples if s.concentration is None or not s.unit]
        if not missing_results:
            checks_passed += 1
        else:
            factors.append(f"{len(missing_results)} sample(s) missing lab results")

    if not factors:
        factors.append("All documentation present")

    score = (checks_passed / checks_total * 100) if checks_total > 0 else 50.0
    return round(score, 1), factors


def _score_monitoring_compliance(
    diagnostics: list[Diagnostic],
    interventions: list[Intervention],
    actions: list[ActionItem],
) -> tuple[float, list[str]]:
    """Score monitoring compliance dimension (0-100).

    Checks whether monitoring obligations are met: regular inspections,
    action follow-ups, intervention tracking.
    """
    factors: list[str] = []
    sub_scores: list[float] = []

    # Diagnostic recency
    if diagnostics:
        most_recent = max(
            (d.date_inspection or d.created_at for d in diagnostics),
            default=None,
        )
        if most_recent:
            if isinstance(most_recent, datetime):
                days_since = (datetime.now(UTC) - most_recent.replace(tzinfo=UTC)).days
            else:
                days_since = (datetime.now(UTC).date() - most_recent).days
            if days_since <= 365:
                sub_scores.append(100)
            elif days_since <= 730:
                sub_scores.append(70)
                factors.append("Last inspection >1 year ago")
            elif days_since <= 1825:
                sub_scores.append(40)
                factors.append("Last inspection >2 years ago")
            else:
                sub_scores.append(10)
                factors.append("Last inspection >5 years ago")
        else:
            sub_scores.append(50)
    else:
        sub_scores.append(20)
        factors.append("No inspections recorded")

    # Action follow-up: ratio of completed/closed vs total
    if actions:
        resolved = [a for a in actions if a.status in ("completed", "closed")]
        ratio = len(resolved) / len(actions)
        sub_scores.append(ratio * 100)
        if ratio < 0.5:
            factors.append(f"Only {len(resolved)}/{len(actions)} actions resolved")
    else:
        sub_scores.append(80)  # No actions needed = decent score

    # Intervention completion
    if interventions:
        completed_interventions = [i for i in interventions if i.status == "completed"]
        ratio = len(completed_interventions) / len(interventions)
        sub_scores.append(ratio * 100)
        if ratio < 1.0:
            pending = len(interventions) - len(completed_interventions)
            factors.append(f"{pending} intervention(s) not completed")
    else:
        sub_scores.append(70)

    if not factors:
        factors.append("Monitoring obligations up to date")

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 50.0
    return round(min(100, max(0, score)), 1), factors


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


async def _fetch_building_data(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch all data needed for health index calculation."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))
    plans = list(plan_result.scalars().all())

    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    # Fetch zones -> elements
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())
    elements: list[BuildingElement] = []
    if zones:
        zone_ids = [z.id for z in zones]
        el_result = await db.execute(select(BuildingElement).where(BuildingElement.zone_id.in_(zone_ids)))
        elements = list(el_result.scalars().all())

    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    return {
        "building": building,
        "diagnostics": diagnostics,
        "samples": samples,
        "documents": documents,
        "plans": plans,
        "actions": actions,
        "elements": elements,
        "interventions": interventions,
    }


def _compute_dimensions(data: dict) -> list[DimensionScore]:
    """Compute all dimension scores from fetched data."""
    building = data["building"]
    diagnostics = data["diagnostics"]
    samples = data["samples"]
    documents = data["documents"]
    plans = data["plans"]
    actions = data["actions"]
    elements = data["elements"]
    interventions = data["interventions"]

    scorers = {
        "pollutant_status": lambda: _score_pollutant_status(samples, diagnostics),
        "structural_condition": lambda: _score_structural_condition(elements, building),
        "compliance": lambda: _score_compliance(samples, diagnostics, actions),
        "documentation_completeness": lambda: _score_documentation_completeness(diagnostics, documents, plans, samples),
        "monitoring_compliance": lambda: _score_monitoring_compliance(diagnostics, interventions, actions),
    }

    dimensions: list[DimensionScore] = []
    for dim_name, scorer in scorers.items():
        score, factors = scorer()
        weight = DIMENSION_WEIGHTS[dim_name]
        dimensions.append(
            DimensionScore(
                dimension=dim_name,
                score=score,
                weight=weight,
                weighted_score=round(score * weight, 2),
                contributing_factors=factors,
            )
        )
    return dimensions


def _compute_trend(
    actions: list[ActionItem],
    interventions: list[Intervention],
) -> str:
    """Determine trend based on recent activity."""
    now = datetime.now(UTC)

    # Check recent completed interventions (last 90 days)
    recent_completed = 0
    for i in interventions:
        if i.status == "completed" and i.date_end:
            days = (now.date() - i.date_end).days
            if 0 <= days <= 90:
                recent_completed += 1

    # Check recently opened critical actions
    recent_critical = 0
    for a in actions:
        if a.status == "open" and a.priority in ("critical", "high") and a.created_at:
            created = a.created_at
            if not created.tzinfo:
                created = created.replace(tzinfo=UTC)
            if (now - created).days <= 90:
                recent_critical += 1

    if recent_completed > 0 and recent_critical == 0:
        return "improving"
    if recent_critical > recent_completed:
        return "declining"
    return "stable"


# ---------------------------------------------------------------------------
# Public API — FN1: calculate_health_index
# ---------------------------------------------------------------------------


async def calculate_health_index(db: AsyncSession, building_id: UUID) -> HealthIndex:
    """Calculate composite 0-100 health index for a building."""
    data = await _fetch_building_data(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    dimensions = _compute_dimensions(data)
    overall = round(sum(d.weighted_score for d in dimensions), 1)
    grade = _score_to_grade(overall)
    trend = _compute_trend(data["actions"], data["interventions"])

    return HealthIndex(
        building_id=building_id,
        overall_score=overall,
        grade=grade,
        trend=trend,
        dimensions=dimensions,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Public API — FN2: get_health_breakdown
# ---------------------------------------------------------------------------


async def get_health_breakdown(db: AsyncSession, building_id: UUID) -> HealthBreakdown:
    """Get detailed per-dimension breakdown with improvement levers."""
    data = await _fetch_building_data(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    dimensions = _compute_dimensions(data)
    overall = round(sum(d.weighted_score for d in dimensions), 1)
    grade = _score_to_grade(overall)

    # Worst contributors: dimensions with lowest scores
    sorted_dims = sorted(dimensions, key=lambda d: d.score)
    worst_contributors = [
        f"{d.dimension}: {d.score}/100 — {', '.join(d.contributing_factors)}" for d in sorted_dims[:3] if d.score < 80
    ]

    # Improvement levers: ranked by potential gain (weight * gap)
    levers: list[ImprovementLever] = []
    for d in sorted_dims:
        gap = 100 - d.score
        if gap < 5:
            continue
        potential_gain = round(gap * d.weight, 1)
        if d.score < 40:
            effort = "high"
        elif d.score < 70:
            effort = "medium"
        else:
            effort = "low"
        desc = _lever_description(d.dimension, d.contributing_factors)
        levers.append(
            ImprovementLever(
                dimension=d.dimension,
                description=desc,
                potential_gain=potential_gain,
                effort=effort,
                priority=0,  # Will be set below
            )
        )

    # Sort by potential gain desc, assign priority
    levers.sort(key=lambda lv: lv.potential_gain, reverse=True)
    for idx, lv in enumerate(levers):
        lv.priority = idx + 1

    return HealthBreakdown(
        building_id=building_id,
        overall_score=overall,
        grade=grade,
        dimensions=dimensions,
        worst_contributors=worst_contributors,
        improvement_levers=levers,
        evaluated_at=datetime.now(UTC),
    )


def _lever_description(dimension: str, factors: list[str]) -> str:
    """Generate a human-readable improvement lever description."""
    descriptions = {
        "pollutant_status": "Complete pollutant evaluations and remediate threshold exceedances",
        "structural_condition": "Address structural deficiencies and schedule condition assessments",
        "compliance": "Resolve compliance gaps: notifications, classifications, open actions",
        "documentation_completeness": "Upload missing reports, lab analyses, and floor plans",
        "monitoring_compliance": "Schedule inspections and complete pending interventions",
    }
    base = descriptions.get(dimension, f"Improve {dimension}")
    if factors and factors[0] != base:
        return f"{base} ({factors[0]})"
    return base


# ---------------------------------------------------------------------------
# Public API — FN3: predict_health_trajectory
# ---------------------------------------------------------------------------


async def predict_health_trajectory(
    db: AsyncSession,
    building_id: UUID,
) -> HealthTrajectory:
    """Project 12-month health trajectory with decay and improvement curves."""
    data = await _fetch_building_data(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    dimensions = _compute_dimensions(data)
    current_score = round(sum(d.weighted_score for d in dimensions), 1)

    # Decay curve: exponential decay capped at floor
    decay_curve: list[TrajectoryPoint] = []
    for month in range(1, 13):
        decayed = current_score * math.exp(-0.02 * month)
        decay_curve.append(TrajectoryPoint(month=month, score=round(max(5, decayed), 1)))

    # Improvement curve: planned interventions boost score
    planned_interventions = [i for i in data["interventions"] if i.status == "planned"]
    open_actions = [a for a in data["actions"] if a.status in ("open", "in_progress")]

    # Estimate monthly improvement if interventions are executed
    improvement_per_month = 0.0
    if planned_interventions:
        improvement_per_month += min(len(planned_interventions) * 2.0, 8.0)
    if open_actions:
        improvement_per_month += min(len(open_actions) * 0.5, 4.0)

    improvement_curve: list[TrajectoryPoint] = []
    for month in range(1, 13):
        improved = min(100, current_score + improvement_per_month * month)
        improvement_curve.append(TrajectoryPoint(month=month, score=round(improved, 1)))

    # Recommended actions from worst dimensions
    sorted_dims = sorted(dimensions, key=lambda d: d.score)
    recommended: list[RecommendedAction] = []
    for d in sorted_dims[:3]:
        gap = 100 - d.score
        if gap < 5:
            continue
        recommended.append(
            RecommendedAction(
                description=_lever_description(d.dimension, d.contributing_factors),
                expected_gain=round(gap * d.weight, 1),
                dimension=d.dimension,
            )
        )

    return HealthTrajectory(
        building_id=building_id,
        current_score=current_score,
        decay_curve=decay_curve,
        improvement_curve=improvement_curve,
        recommended_actions=recommended,
        projected_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Public API — FN4: get_portfolio_health_dashboard
# ---------------------------------------------------------------------------


async def get_portfolio_health_dashboard(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioHealthDashboard:
    """Org-level health dashboard across all buildings."""
    from app.services.building_data_loader import load_org_buildings

    # Get buildings created by users in this org
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return _empty_portfolio_dashboard(org_id)

    # Calculate health for each building
    summaries: list[BuildingHealthSummary] = []
    for b in buildings:
        data = await _fetch_building_data(db, b.id)
        if data is None:
            continue
        dimensions = _compute_dimensions(data)
        score = round(sum(d.weighted_score for d in dimensions), 1)
        grade = _score_to_grade(score)
        trend = _compute_trend(data["actions"], data["interventions"])
        summaries.append(
            BuildingHealthSummary(
                building_id=b.id,
                address=b.address,
                city=b.city,
                score=score,
                grade=grade,
                trend=trend,
            )
        )

    if not summaries:
        return _empty_portfolio_dashboard(org_id)

    # Aggregate
    avg_score = round(sum(s.score for s in summaries) / len(summaries), 1)
    avg_grade = _score_to_grade(avg_score)

    # Health distribution
    distribution: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    for s in summaries:
        distribution[s.grade] = distribution.get(s.grade, 0) + 1

    # Trend: majority vote
    trend_counts = {"improving": 0, "stable": 0, "declining": 0}
    for s in summaries:
        trend_counts[s.trend] = trend_counts.get(s.trend, 0) + 1
    portfolio_trend = max(trend_counts, key=trend_counts.get)  # type: ignore[arg-type]

    # Best / worst
    sorted_summaries = sorted(summaries, key=lambda s: s.score)
    worst = sorted_summaries[:5]
    best = sorted_summaries[-5:][::-1]

    # Threshold crossings (below 50)
    threshold_crossings = [s for s in summaries if s.score < 50]

    # Aggregate improvement cost estimate: CHF 5000 per point below 80, per building
    total_cost = sum(max(0, 80 - s.score) * 5000 for s in summaries)

    return PortfolioHealthDashboard(
        organization_id=org_id,
        building_count=len(summaries),
        average_score=avg_score,
        average_grade=avg_grade,
        health_distribution=distribution,
        trend=portfolio_trend,
        best_buildings=best,
        worst_buildings=worst,
        threshold_crossings=threshold_crossings,
        aggregate_improvement_cost_chf=total_cost,
        evaluated_at=datetime.now(UTC),
    )


def _empty_portfolio_dashboard(org_id: UUID) -> PortfolioHealthDashboard:
    return PortfolioHealthDashboard(
        organization_id=org_id,
        building_count=0,
        average_score=0.0,
        average_grade="F",
        health_distribution={"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0},
        trend="stable",
        best_buildings=[],
        worst_buildings=[],
        threshold_crossings=[],
        aggregate_improvement_cost_chf=0.0,
        evaluated_at=datetime.now(UTC),
    )
