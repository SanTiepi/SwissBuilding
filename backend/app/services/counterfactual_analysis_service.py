"""
SwissBuildingOS - Counterfactual Analysis Service

Provides what-if / counterfactual analysis, stress testing, timeline
alternatives, and portfolio-level stress testing for building pollutant
diagnostics.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.counterfactual_analysis import (
    BuildingTimelineAnalysis,
    CounterfactualResult,
    CounterfactualScenario,
    ImpactMetric,
    PortfolioStressTest,
    StressTestParameter,
    StressTestResult,
    TimelineAlternative,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Cost constants (CHF, simplified Swiss market rates)
# ---------------------------------------------------------------------------

_REMEDIATION_COST_PER_M2: dict[str, float] = {
    "asbestos": 120.0,
    "pcb": 150.0,
    "lead": 80.0,
    "hap": 100.0,
    "radon": 15.0,
}

_RISK_LEVEL_MULTIPLIER: dict[str, float] = {
    "critical": 2.0,
    "high": 1.5,
    "medium": 1.0,
    "low": 0.5,
    "unknown": 0.7,
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _fetch_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _count_actions(db: AsyncSession, building_id: UUID) -> int:
    result = await db.execute(select(func.count()).select_from(ActionItem).where(ActionItem.building_id == building_id))
    return result.scalar() or 0


def _surface(building: Building) -> float:
    return building.surface_area_m2 or 200.0


def _baseline_cost(samples: list[Sample], building: Building) -> float:
    area = _surface(building)
    cost = 0.0
    seen: set[str] = set()
    for s in samples:
        pt = s.pollutant_type
        if pt and pt not in seen:
            seen.add(pt)
            cost += _REMEDIATION_COST_PER_M2.get(pt, 100.0) * area
    return cost


def _dominant_risk(samples: list[Sample]) -> str:
    priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    best = "unknown"
    for s in samples:
        rl = s.risk_level or "unknown"
        if priority.get(rl, 0) > priority.get(best, 0):
            best = rl
    return best


def _direction(delta: float) -> str:
    if delta < 0:
        return "better"
    if delta > 0:
        return "worse"
    return "neutral"


def _direction_inverse(delta: float) -> str:
    """For metrics where higher is worse (cost, violations)."""
    if delta > 0:
        return "worse"
    if delta < 0:
        return "better"
    return "neutral"


# ---------------------------------------------------------------------------
# FN1 — run_counterfactual
# ---------------------------------------------------------------------------


async def run_counterfactual(
    building_id: UUID,
    scenario_type: str,
    db: AsyncSession,
) -> CounterfactualResult:
    """Run a counterfactual scenario on a building."""
    building = await _fetch_building(db, building_id)
    samples = await _fetch_samples(db, building_id)
    action_count = await _count_actions(db, building_id)

    base_cost = _baseline_cost(samples, building)
    base_risk = _dominant_risk(samples)
    risk_mult = _RISK_LEVEL_MULTIPLIER.get(base_risk, 1.0)
    exceeded_count = sum(1 for s in samples if s.threshold_exceeded)

    impacts: list[ImpactMetric] = []
    overall_impact = "neutral"
    risk_level_change: str | None = None
    cost_impact = 0.0

    if scenario_type == "delayed_action":
        cf_cost = base_cost * 1.3
        cost_delta = cf_cost - base_cost
        cf_violations = int(exceeded_count * 1.5) + 1
        violation_delta = cf_violations - exceeded_count

        impacts = [
            ImpactMetric(
                metric_name="remediation_cost",
                baseline_value=base_cost,
                counterfactual_value=cf_cost,
                delta=cost_delta,
                delta_pct=30.0,
                unit="CHF",
                direction="worse",
            ),
            ImpactMetric(
                metric_name="violations",
                baseline_value=float(exceeded_count),
                counterfactual_value=float(cf_violations),
                delta=float(violation_delta),
                delta_pct=50.0 if exceeded_count > 0 else 100.0,
                unit="count",
                direction="worse",
            ),
            ImpactMetric(
                metric_name="risk_level",
                baseline_value=risk_mult,
                counterfactual_value=min(risk_mult * 1.5, 2.0),
                delta=min(risk_mult * 0.5, 2.0 - risk_mult),
                delta_pct=50.0,
                unit="multiplier",
                direction="worse",
            ),
        ]
        overall_impact = "negative"
        risk_level_change = f"{base_risk} → higher"
        cost_impact = cost_delta

        scenario = CounterfactualScenario(
            scenario_id=str(_uuid.uuid4()),
            scenario_type="delayed_action",
            description="What if remediation is delayed by 2 years?",
            parameters={"delay_years": "2", "cost_increase_pct": "30"},
        )

    elif scenario_type == "early_intervention":
        cf_cost = base_cost * 0.8
        cost_delta = cf_cost - base_cost
        cf_violations = max(0, exceeded_count - 2)
        violation_delta = cf_violations - exceeded_count

        impacts = [
            ImpactMetric(
                metric_name="remediation_cost",
                baseline_value=base_cost,
                counterfactual_value=cf_cost,
                delta=cost_delta,
                delta_pct=-20.0,
                unit="CHF",
                direction="better",
            ),
            ImpactMetric(
                metric_name="violations",
                baseline_value=float(exceeded_count),
                counterfactual_value=float(cf_violations),
                delta=float(violation_delta),
                delta_pct=-40.0 if exceeded_count > 0 else 0.0,
                unit="count",
                direction="better",
            ),
        ]
        overall_impact = "positive"
        risk_level_change = f"{base_risk} → lower"
        cost_impact = cost_delta

        scenario = CounterfactualScenario(
            scenario_id=str(_uuid.uuid4()),
            scenario_type="early_intervention",
            description="What if action had been taken 2 years earlier?",
            parameters={"earlier_years": "2", "cost_reduction_pct": "20"},
        )

    elif scenario_type == "regulation_change":
        cf_violations = sum(1 for s in samples if s.concentration and s.concentration > 0)
        violation_delta = cf_violations - exceeded_count
        cf_cost = base_cost * 1.4

        impacts = [
            ImpactMetric(
                metric_name="violations",
                baseline_value=float(exceeded_count),
                counterfactual_value=float(cf_violations),
                delta=float(violation_delta),
                delta_pct=(violation_delta / max(exceeded_count, 1)) * 100,
                unit="count",
                direction=_direction_inverse(float(violation_delta)),
            ),
            ImpactMetric(
                metric_name="remediation_cost",
                baseline_value=base_cost,
                counterfactual_value=cf_cost,
                delta=cf_cost - base_cost,
                delta_pct=40.0,
                unit="CHF",
                direction="worse",
            ),
        ]
        overall_impact = "negative"
        risk_level_change = f"{base_risk} → higher"
        cost_impact = cf_cost - base_cost

        scenario = CounterfactualScenario(
            scenario_id=str(_uuid.uuid4()),
            scenario_type="regulation_change",
            description="What if regulatory thresholds tighten by 50%?",
            parameters={"threshold_reduction_pct": "50"},
        )

    elif scenario_type == "budget_cut":
        feasible = max(0, action_count - int(action_count * 0.4))
        residual_pct = 40.0
        cf_cost = base_cost * 0.6

        impacts = [
            ImpactMetric(
                metric_name="feasible_interventions",
                baseline_value=float(action_count),
                counterfactual_value=float(feasible),
                delta=float(feasible - action_count),
                delta_pct=-40.0,
                unit="count",
                direction="worse",
            ),
            ImpactMetric(
                metric_name="residual_risk_pct",
                baseline_value=0.0,
                counterfactual_value=residual_pct,
                delta=residual_pct,
                delta_pct=100.0,
                unit="%",
                direction="worse",
            ),
        ]
        overall_impact = "negative"
        risk_level_change = f"{base_risk} → higher"
        cost_impact = -(base_cost * 0.4)

        scenario = CounterfactualScenario(
            scenario_id=str(_uuid.uuid4()),
            scenario_type="budget_cut",
            description="What if budget is reduced by 40%?",
            parameters={"budget_reduction_pct": "40"},
        )

    else:
        # natural_event or unknown — generic impact
        cf_cost = base_cost * 1.2
        impacts = [
            ImpactMetric(
                metric_name="remediation_cost",
                baseline_value=base_cost,
                counterfactual_value=cf_cost,
                delta=cf_cost - base_cost,
                delta_pct=20.0,
                unit="CHF",
                direction="worse",
            ),
        ]
        overall_impact = "negative"
        cost_impact = cf_cost - base_cost

        scenario = CounterfactualScenario(
            scenario_id=str(_uuid.uuid4()),
            scenario_type=scenario_type,
            description=f"What-if scenario: {scenario_type}",
            parameters={},
        )

    return CounterfactualResult(
        building_id=building_id,
        scenario=scenario,
        impacts=impacts,
        overall_impact=overall_impact,
        risk_level_change=risk_level_change,
        cost_impact_chf=cost_impact,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 — run_stress_test
# ---------------------------------------------------------------------------


async def run_stress_test(
    building_id: UUID,
    stress_type: str,
    db: AsyncSession,
) -> StressTestResult:
    """Apply stress parameters to a building and evaluate resilience."""
    building = await _fetch_building(db, building_id)
    samples = await _fetch_samples(db, building_id)
    base_cost = _baseline_cost(samples, building)
    exceeded_count = sum(1 for s in samples if s.threshold_exceeded)

    parameters: list[StressTestParameter] = []
    new_violations = 0
    additional_cost = 0.0
    checks_passed = 0
    total_checks = 4

    if stress_type == "regulatory_tightening":
        new_violations = sum(1 for s in samples if s.concentration and not s.threshold_exceeded and s.concentration > 0)
        parameters = [
            StressTestParameter(
                parameter_name="threshold_factor",
                baseline=1.0,
                stressed=0.5,
                unit="multiplier",
            ),
        ]
        additional_cost = new_violations * 5000.0
        checks_passed = 3 if new_violations == 0 else (1 if new_violations <= 2 else 0)

    elif stress_type == "cost_increase":
        additional_cost = base_cost * 0.5
        parameters = [
            StressTestParameter(
                parameter_name="cost_multiplier",
                baseline=1.0,
                stressed=1.5,
                unit="multiplier",
            ),
        ]
        new_violations = 0
        checks_passed = 2 if base_cost < 50_000 else 1

    elif stress_type == "timeline_acceleration":
        parameters = [
            StressTestParameter(
                parameter_name="deadline_factor",
                baseline=1.0,
                stressed=0.5,
                unit="multiplier",
            ),
        ]
        new_violations = max(0, exceeded_count - 1)
        additional_cost = base_cost * 0.3
        checks_passed = 2

    elif stress_type == "resource_scarcity":
        parameters = [
            StressTestParameter(
                parameter_name="contractor_availability",
                baseline=1.0,
                stressed=0.7,
                unit="ratio",
            ),
        ]
        new_violations = 0
        additional_cost = base_cost * 0.2
        checks_passed = 3

    else:
        parameters = [
            StressTestParameter(
                parameter_name="generic_stress",
                baseline=1.0,
                stressed=1.5,
                unit="multiplier",
            ),
        ]
        additional_cost = base_cost * 0.25
        checks_passed = 2

    resilience = checks_passed / total_checks
    buildings_failing = 1 if resilience < 0.5 else 0

    return StressTestResult(
        building_id=building_id,
        stress_type=stress_type,
        parameters=parameters,
        buildings_failing=buildings_failing,
        new_violations=new_violations,
        additional_cost=additional_cost,
        resilience_score=round(resilience, 2),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3 — analyze_timeline_alternatives
# ---------------------------------------------------------------------------


async def analyze_timeline_alternatives(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingTimelineAnalysis:
    """Generate 3 timeline alternatives for building remediation."""
    building = await _fetch_building(db, building_id)
    samples = await _fetch_samples(db, building_id)
    base_cost = _baseline_cost(samples, building)

    today = date.today()

    # Standard timeline: 12 months
    standard_start = today
    standard_end = today + timedelta(days=365)
    standard_cost = base_cost
    standard_risk_reduction = 70.0

    # Accelerated: 6 months, 20% more expensive, 90% risk reduction
    accel_end = today + timedelta(days=182)
    accel_cost = base_cost * 1.2
    accel_risk_reduction = 90.0

    # Extended: 18 months, 15% cheaper, 50% risk reduction
    extended_end = today + timedelta(days=548)
    extended_cost = base_cost * 0.85
    extended_risk_reduction = 50.0

    # Best cost/risk ratio = risk_reduction / cost (higher is better)
    ratios = {
        "accelerated": accel_risk_reduction / max(accel_cost, 1.0),
        "standard": standard_risk_reduction / max(standard_cost, 1.0),
        "extended": extended_risk_reduction / max(extended_cost, 1.0),
    }
    optimal_key = max(ratios, key=ratios.get)  # type: ignore[arg-type]

    alternatives = [
        TimelineAlternative(
            alternative_id="accelerated",
            description="Accelerated remediation: 50% faster, 20% more expensive, 90% risk reduction",
            start_date=standard_start,
            completion_date=accel_end,
            total_cost=accel_cost,
            risk_reduction_pct=accel_risk_reduction,
            is_optimal=(optimal_key == "accelerated"),
        ),
        TimelineAlternative(
            alternative_id="standard",
            description="Standard pace: baseline cost, 70% risk reduction",
            start_date=standard_start,
            completion_date=standard_end,
            total_cost=standard_cost,
            risk_reduction_pct=standard_risk_reduction,
            is_optimal=(optimal_key == "standard"),
        ),
        TimelineAlternative(
            alternative_id="extended",
            description="Extended timeline: 50% slower, 15% cheaper, 50% risk reduction",
            start_date=standard_start,
            completion_date=extended_end,
            total_cost=extended_cost,
            risk_reduction_pct=extended_risk_reduction,
            is_optimal=(optimal_key == "extended"),
        ),
    ]

    optimal_alt = next(a for a in alternatives if a.is_optimal)
    optimal_savings = standard_cost - optimal_alt.total_cost

    return BuildingTimelineAnalysis(
        building_id=building_id,
        current_timeline_cost=standard_cost,
        alternatives=alternatives,
        optimal_savings=optimal_savings,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 — run_portfolio_stress_test
# ---------------------------------------------------------------------------


async def run_portfolio_stress_test(
    org_id: UUID,
    stress_type: str,
    db: AsyncSession,
) -> PortfolioStressTest:
    """Run a stress test across all buildings in an organization."""
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if org is None:
        raise ValueError(f"Organization {org_id} not found")

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioStressTest(
            organization_id=org_id,
            stress_type=stress_type,
            total_buildings_tested=0,
            buildings_resilient=0,
            buildings_at_risk=0,
            average_resilience_score=0.0,
            total_additional_cost=0.0,
            generated_at=datetime.now(UTC),
        )

    total_tested = len(buildings)
    resilient = 0
    at_risk = 0
    total_cost = 0.0
    total_resilience = 0.0

    for b in buildings:
        result = await run_stress_test(b.id, stress_type, db)
        total_cost += result.additional_cost
        total_resilience += result.resilience_score
        if result.resilience_score >= 0.5:
            resilient += 1
        else:
            at_risk += 1

    return PortfolioStressTest(
        organization_id=org_id,
        stress_type=stress_type,
        total_buildings_tested=total_tested,
        buildings_resilient=resilient,
        buildings_at_risk=at_risk,
        average_resilience_score=round(total_resilience / total_tested, 2),
        total_additional_cost=total_cost,
        generated_at=datetime.now(UTC),
    )
