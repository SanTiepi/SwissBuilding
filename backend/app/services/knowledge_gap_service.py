"""
SwissBuildingOS - Knowledge Gap Service

Identifies what we *don't* know about a building's pollutant situation,
ranks investigation priorities by ROI, and computes knowledge completeness
scores suitable for radar-chart visualisation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.knowledge_gap import (
    BuildingKnowledgeSummary,
    DocumentSubScore,
    InvestigationPriority,
    InvestigationPriorityResult,
    KnowledgeCompletenessResult,
    KnowledgeGap,
    KnowledgeGapResult,
    PollutantSubScore,
    PortfolioKnowledgeOverview,
    RadarChartAxis,
    ZoneSubScore,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_POLLUTANTS = ("asbestos", "pcb", "lead", "hap", "radon")

REQUIRED_DOCUMENT_TYPES = (
    "diagnostic_report",
    "lab_report",
    "floor_plan",
    "site_plan",
    "photo_documentation",
)

DIAGNOSTIC_VALIDITY_YEARS = 5

# Rough cost estimates (CHF) for closing a gap — used for ROI ranking
_COST_ESTIMATES: dict[str, float] = {
    "undiagnosed_pollutant": 2500.0,
    "unsampled_zone": 1500.0,
    "outdated_diagnostic": 3000.0,
    "conflicting_results": 2000.0,
    "missing_document": 500.0,
}

# Severity → risk-reduction value when gap is closed
_RISK_REDUCTION: dict[str, float] = {
    "critical": 0.9,
    "high": 0.7,
    "medium": 0.4,
    "low": 0.2,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building_data(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[Building | None, list[Diagnostic], list[Sample], list[Zone], list[Document]]:
    """Fetch all data needed for gap analysis in parallel-safe queries."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None, [], [], [], []

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    return building, diagnostics, samples, zones, documents


def _pollutant_severity(pollutant: str) -> str:
    """Severity of not having evaluated a pollutant."""
    if pollutant in ("asbestos", "lead"):
        return "critical"
    if pollutant in ("pcb", "radon"):
        return "high"
    return "medium"


def _is_outdated(diag: Diagnostic, now: datetime) -> bool:
    """Check if a diagnostic is older than DIAGNOSTIC_VALIDITY_YEARS."""
    ref_date = diag.date_report or diag.date_inspection
    if ref_date is None:
        return False
    ref_dt = datetime(ref_date.year, ref_date.month, ref_date.day, tzinfo=UTC)
    age_days = (now - ref_dt).days
    return age_days > DIAGNOSTIC_VALIDITY_YEARS * 365


# ---------------------------------------------------------------------------
# FN1: analyze_knowledge_gaps
# ---------------------------------------------------------------------------


async def analyze_knowledge_gaps(
    db: AsyncSession,
    building_id: UUID,
) -> KnowledgeGapResult:
    """Identify what we don't know about a building."""
    now = datetime.now(UTC)
    building, diagnostics, samples, zones, documents = await _fetch_building_data(db, building_id)

    gaps: list[KnowledgeGap] = []

    if building is None:
        return KnowledgeGapResult(
            building_id=building_id,
            gaps=[],
            total_gaps=0,
            critical_count=0,
            high_count=0,
            evaluated_at=now,
        )

    # 1. Undiagnosed pollutants
    evaluated_pollutants = {(s.pollutant_type or "").lower() for s in samples} & set(ALL_POLLUTANTS)
    for p in ALL_POLLUTANTS:
        if p not in evaluated_pollutants:
            sev = _pollutant_severity(p)
            gaps.append(
                KnowledgeGap(
                    id=f"undiagnosed_{p}",
                    gap_type="undiagnosed_pollutant",
                    severity=sev,
                    description=f"No samples exist for {p}",
                    location=None,
                    recommended_action=f"Commission {p} diagnostic sampling",
                )
            )

    # 2. Zones never sampled
    if zones:
        # Find which zones have at least one sample (by matching location_floor/location_room)
        sampled_zone_names = set()
        for s in samples:
            if s.location_room:
                sampled_zone_names.add(s.location_room.lower())
            if s.location_floor:
                sampled_zone_names.add(s.location_floor.lower())

        for z in zones:
            zone_name_lower = (z.name or "").lower()
            if zone_name_lower and zone_name_lower not in sampled_zone_names:
                gaps.append(
                    KnowledgeGap(
                        id=f"unsampled_zone_{z.id}",
                        gap_type="unsampled_zone",
                        severity="medium",
                        description=f"Zone '{z.name}' has never been sampled",
                        location=z.name,
                        recommended_action=f"Collect samples in zone '{z.name}'",
                    )
                )

    # 3. Outdated diagnostics (>5yr)
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    for d in completed_diags:
        if _is_outdated(d, now):
            ref = d.date_report or d.date_inspection
            gaps.append(
                KnowledgeGap(
                    id=f"outdated_diag_{d.id}",
                    gap_type="outdated_diagnostic",
                    severity="high",
                    description=f"Diagnostic from {ref} is older than {DIAGNOSTIC_VALIDITY_YEARS} years",
                    location=None,
                    recommended_action="Commission updated diagnostic",
                )
            )

    # 4. Conflicting results — samples of same pollutant with contradictory risk levels
    from collections import defaultdict

    pollutant_risks: dict[str, set[str]] = defaultdict(set)
    for s in samples:
        pt = (s.pollutant_type or "").lower()
        rl = (s.risk_level or "").lower()
        if pt and rl:
            pollutant_risks[pt].add(rl)

    conflicting_pairs = {("low", "high"), ("low", "critical"), ("medium", "critical")}
    for pt, risk_levels in pollutant_risks.items():
        for a, b in conflicting_pairs:
            if a in risk_levels and b in risk_levels:
                gaps.append(
                    KnowledgeGap(
                        id=f"conflict_{pt}_{a}_{b}",
                        gap_type="conflicting_results",
                        severity="high",
                        description=f"Conflicting risk levels ({a} vs {b}) for {pt}",
                        location=None,
                        recommended_action=f"Investigate conflicting {pt} results and reconcile",
                    )
                )
                break  # one gap per pollutant

    # 5. Missing document types
    existing_doc_types = {(d.document_type or "").lower() for d in documents}
    for dt in REQUIRED_DOCUMENT_TYPES:
        if dt not in existing_doc_types:
            gaps.append(
                KnowledgeGap(
                    id=f"missing_doc_{dt}",
                    gap_type="missing_document",
                    severity="low" if dt == "photo_documentation" else "medium",
                    description=f"Missing document: {dt.replace('_', ' ')}",
                    location=None,
                    recommended_action=f"Upload {dt.replace('_', ' ')}",
                )
            )

    critical_count = sum(1 for g in gaps if g.severity == "critical")
    high_count = sum(1 for g in gaps if g.severity == "high")

    return KnowledgeGapResult(
        building_id=building_id,
        gaps=gaps,
        total_gaps=len(gaps),
        critical_count=critical_count,
        high_count=high_count,
        evaluated_at=now,
    )


# ---------------------------------------------------------------------------
# FN2: get_investigation_priorities
# ---------------------------------------------------------------------------


async def get_investigation_priorities(
    db: AsyncSession,
    building_id: UUID,
) -> InvestigationPriorityResult:
    """Rank what to investigate next by ROI."""
    gap_result = await analyze_knowledge_gaps(db, building_id)
    now = datetime.now(UTC)

    priorities: list[InvestigationPriority] = []
    for gap in gap_result.gaps:
        cost = _COST_ESTIMATES.get(gap.gap_type, 1000.0)
        risk_red = _RISK_REDUCTION.get(gap.severity, 0.3)
        roi = risk_red / cost * 1000 if cost > 0 else 0.0

        priorities.append(
            InvestigationPriority(
                rank=0,  # assigned after sorting
                gap_type=gap.gap_type,
                description=gap.description,
                location=gap.location,
                estimated_cost_chf=cost,
                risk_reduction_value=risk_red,
                roi_score=round(roi, 4),
            )
        )

    # Sort by ROI descending
    priorities.sort(key=lambda p: p.roi_score, reverse=True)
    for i, p in enumerate(priorities, start=1):
        p.rank = i

    total_cost = sum(p.estimated_cost_chf for p in priorities)

    return InvestigationPriorityResult(
        building_id=building_id,
        priorities=priorities,
        total_estimated_cost_chf=total_cost,
        evaluated_at=now,
    )


# ---------------------------------------------------------------------------
# FN3: estimate_knowledge_completeness
# ---------------------------------------------------------------------------


async def estimate_knowledge_completeness(
    db: AsyncSession,
    building_id: UUID,
) -> KnowledgeCompletenessResult:
    """Compute a 0-100 knowledge completeness score with sub-scores."""
    now = datetime.now(UTC)
    building, diagnostics, samples, zones, documents = await _fetch_building_data(db, building_id)

    if building is None:
        return KnowledgeCompletenessResult(
            building_id=building_id,
            overall_score=0.0,
            pollutant_scores=[],
            zone_scores=[],
            document_scores=[],
            radar_chart=[],
            evaluated_at=now,
        )

    evaluated_pollutants = {(s.pollutant_type or "").lower() for s in samples} & set(ALL_POLLUTANTS)

    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    has_recent_diag = any(not _is_outdated(d, now) for d in completed_diags) if completed_diags else False

    # Pollutant sub-scores
    pollutant_scores: list[PollutantSubScore] = []
    for p in ALL_POLLUTANTS:
        has_samples = p in evaluated_pollutants
        has_diag = any((s.pollutant_type or "").lower() == p for s in samples)
        recent = has_diag and has_recent_diag
        score = 0.0
        if has_samples:
            score = 100.0 if recent else 60.0
        pollutant_scores.append(
            PollutantSubScore(
                pollutant=p,
                score=score,
                has_diagnostic=has_diag,
                has_samples=has_samples,
                samples_recent=recent,
            )
        )

    # Zone sub-scores
    zone_scores: list[ZoneSubScore] = []
    sampled_zone_names = set()
    for s in samples:
        if s.location_room:
            sampled_zone_names.add(s.location_room.lower())
        if s.location_floor:
            sampled_zone_names.add(s.location_floor.lower())

    if zones:
        for z in zones:
            zone_name_lower = (z.name or "").lower()
            has_s = zone_name_lower in sampled_zone_names if zone_name_lower else False
            zone_scores.append(
                ZoneSubScore(
                    zone_id=z.id,
                    zone_name=z.name,
                    score=100.0 if has_s else 0.0,
                    has_samples=has_s,
                )
            )
    else:
        # No zones defined — that itself is a gap but we score it neutrally
        zone_scores.append(
            ZoneSubScore(
                zone_id=None,
                zone_name="(no zones defined)",
                score=50.0,
                has_samples=False,
            )
        )

    # Document sub-scores
    existing_doc_types = {(d.document_type or "").lower() for d in documents}
    document_scores: list[DocumentSubScore] = []
    for dt in REQUIRED_DOCUMENT_TYPES:
        present = dt in existing_doc_types
        document_scores.append(
            DocumentSubScore(
                document_type=dt,
                score=100.0 if present else 0.0,
                present=present,
            )
        )

    # Overall score: weighted average (pollutants 50%, zones 25%, docs 25%)
    avg_pollutant = sum(ps.score for ps in pollutant_scores) / len(pollutant_scores) if pollutant_scores else 0.0
    avg_zone = sum(zs.score for zs in zone_scores) / len(zone_scores) if zone_scores else 0.0
    avg_doc = sum(ds.score for ds in document_scores) / len(document_scores) if document_scores else 0.0
    overall = round(avg_pollutant * 0.5 + avg_zone * 0.25 + avg_doc * 0.25, 2)

    radar_chart = [
        RadarChartAxis(axis="Pollutants", value=round(avg_pollutant, 1)),
        RadarChartAxis(axis="Zones", value=round(avg_zone, 1)),
        RadarChartAxis(axis="Documents", value=round(avg_doc, 1)),
        RadarChartAxis(axis="Diagnostics", value=100.0 if has_recent_diag else 0.0),
        RadarChartAxis(
            axis="Samples",
            value=round(len(evaluated_pollutants) / len(ALL_POLLUTANTS) * 100, 1),
        ),
    ]

    return KnowledgeCompletenessResult(
        building_id=building_id,
        overall_score=overall,
        pollutant_scores=pollutant_scores,
        zone_scores=zone_scores,
        document_scores=document_scores,
        radar_chart=radar_chart,
        evaluated_at=now,
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_knowledge_overview
# ---------------------------------------------------------------------------


async def get_portfolio_knowledge_overview(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioKnowledgeOverview:
    """Organisation-level knowledge overview across all buildings."""
    now = datetime.now(UTC)

    # Find buildings created by users belonging to this org
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioKnowledgeOverview(
            organization_id=org_id,
            building_count=0,
            avg_completeness=0.0,
            worst_buildings=[],
            most_common_gaps=[],
            estimated_cost_to_80=0.0,
            estimated_cost_to_90=0.0,
            estimated_cost_to_100=0.0,
            evaluated_at=now,
        )

    summaries: list[BuildingKnowledgeSummary] = []
    all_gap_types: list[str] = []

    for b in buildings:
        completeness = await estimate_knowledge_completeness(db, b.id)
        gap_result = await analyze_knowledge_gaps(db, b.id)
        all_gap_types.extend(g.gap_type for g in gap_result.gaps)
        summaries.append(
            BuildingKnowledgeSummary(
                building_id=b.id,
                address=b.address,
                completeness_score=completeness.overall_score,
                gap_count=gap_result.total_gaps,
                critical_gap_count=gap_result.critical_count,
            )
        )

    avg_completeness = round(sum(s.completeness_score for s in summaries) / len(summaries), 2)

    # Worst buildings: sorted by completeness ascending, take top 5
    worst = sorted(summaries, key=lambda s: s.completeness_score)[:5]

    # Most common gap types
    gap_type_counts: dict[str, int] = {}
    for gt in all_gap_types:
        gap_type_counts[gt] = gap_type_counts.get(gt, 0) + 1
    most_common = sorted(gap_type_counts, key=lambda k: gap_type_counts[k], reverse=True)[:5]

    # Estimated costs to reach thresholds
    # Simple model: each building below threshold needs (threshold - current) / 100 * base_cost_per_building
    base_cost = sum(_COST_ESTIMATES.values())  # total cost to close all gap types once

    def _cost_to_threshold(threshold: float) -> float:
        total = 0.0
        for s in summaries:
            if s.completeness_score < threshold:
                gap_fraction = (threshold - s.completeness_score) / 100.0
                total += gap_fraction * base_cost
        return round(total, 2)

    return PortfolioKnowledgeOverview(
        organization_id=org_id,
        building_count=len(buildings),
        avg_completeness=avg_completeness,
        worst_buildings=worst,
        most_common_gaps=most_common,
        estimated_cost_to_80=_cost_to_threshold(80.0),
        estimated_cost_to_90=_cost_to_threshold(90.0),
        estimated_cost_to_100=_cost_to_threshold(100.0),
        evaluated_at=now,
    )
