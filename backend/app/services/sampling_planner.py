"""
SwissBuildingOS - Sampling Planner Service

Analyzes a building and recommends evidence-collection priorities based on
current unknowns, trust gaps, and under-proven zones.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone
from app.schemas.sampling_plan import SamplingPlan, SamplingRecommendation
from app.services import completeness_engine, unknown_generator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pollutant applicability (duplicated from unknown_generator for scoring)
# ---------------------------------------------------------------------------

_POLLUTANT_YEAR_RULES: dict[str, tuple[int | None, int | None]] = {
    "asbestos": (None, 1990),
    "pcb": (1955, 1975),
    "lead": (None, 2006),
    "hap": (None, None),
    "radon": (None, None),
}

# Pollutants with higher inherent risk get a scoring bonus
_POLLUTANT_RISK_WEIGHT: dict[str, float] = {
    "asbestos": 0.05,
    "pcb": 0.03,
    "lead": 0.03,
    "hap": 0.02,
    "radon": 0.02,
}

# Diagnostic considered obsolete after this many years
_OBSOLETE_YEARS = 5

# Unknown type → recommendation action_type mapping
_UNKNOWN_TO_ACTION: dict[str, str] = {
    "missing_diagnostic": "sample_pollutant",
    "missing_pollutant_evaluation": "sample_pollutant",
    "uninspected_zone": "visual_inspection",
    "unconfirmed_material": "confirm_material",
    "missing_plan": "upload_plan",
    "undocumented_intervention": "document_intervention",
    "missing_lab_results": "lab_analysis",
}


# ---------------------------------------------------------------------------
# Impact scoring
# ---------------------------------------------------------------------------


def _base_impact(unknown: UnknownIssue) -> float:
    """Compute base impact score from unknown severity and readiness blocking."""
    if unknown.blocks_readiness:
        return 0.95
    severity_map = {"critical": 0.85, "high": 0.75, "medium": 0.5, "low": 0.25}
    return severity_map.get(unknown.severity, 0.3)


def _impact_to_priority(impact: float) -> str:
    """Map impact score to priority label."""
    if impact >= 0.9:
        return "critical"
    if impact >= 0.7:
        return "high"
    if impact >= 0.4:
        return "medium"
    return "low"


def _extract_pollutant(unknown: UnknownIssue) -> str | None:
    """Extract pollutant name from entity_type like 'pollutant:asbestos'."""
    if unknown.entity_type and unknown.entity_type.startswith("pollutant:"):
        return unknown.entity_type.split(":", 1)[1]
    return None


# ---------------------------------------------------------------------------
# Recommendation builders
# ---------------------------------------------------------------------------


def _build_recommendation_from_unknown(unknown: UnknownIssue) -> SamplingRecommendation:
    """Convert an open UnknownIssue into a SamplingRecommendation."""
    action_type = _UNKNOWN_TO_ACTION.get(unknown.unknown_type, "visual_inspection")
    pollutant = _extract_pollutant(unknown)

    impact = _base_impact(unknown)

    # Bonus for specific pollutant risk
    if pollutant:
        impact = min(1.0, impact + _POLLUTANT_RISK_WEIGHT.get(pollutant, 0.0))

    priority = _impact_to_priority(impact)

    # Use building id as fallback entity_id
    entity_id = unknown.entity_id or unknown.building_id
    entity_type = unknown.entity_type or "building"
    # Normalize pollutant entity types
    if entity_type.startswith("pollutant:"):
        entity_type = "building"

    return SamplingRecommendation(
        action_type=action_type,
        priority=priority,
        impact_score=round(impact, 2),
        description=unknown.title,
        entity_type=entity_type,
        entity_id=entity_id,
        pollutant=pollutant,
        rationale=unknown.description or unknown.title,
    )


def _build_zone_coverage_recommendations(
    zones: list[Zone],
    existing_entity_ids: set[UUID],
) -> list[SamplingRecommendation]:
    """Generate sample_zone recommendations for zones with no elements."""
    recs: list[SamplingRecommendation] = []
    for zone in zones:
        if zone.id in existing_entity_ids:
            continue
        if not zone.elements:
            recs.append(
                SamplingRecommendation(
                    action_type="sample_zone",
                    priority="high",
                    impact_score=0.8,
                    description=f"Take samples in uninspected zone: {zone.name}",
                    entity_type="zone",
                    entity_id=zone.id,
                    pollutant=None,
                    rationale=f"Zone '{zone.name}' has no elements or materials defined. "
                    "Sampling is needed to establish pollutant baseline.",
                ),
            )
    return recs


def _build_obsolete_diagnostic_recommendations(
    diagnostics: list[Diagnostic],
    existing_entity_ids: set[UUID],
) -> list[SamplingRecommendation]:
    """Generate refresh_diagnostic for diagnostics older than 5 years."""
    recs: list[SamplingRecommendation] = []
    now = datetime.now(UTC)
    for diag in diagnostics:
        if diag.id in existing_entity_ids:
            continue
        if diag.status not in ("completed", "validated"):
            continue
        if diag.date_inspection is None:
            continue
        # date_inspection can be date or datetime
        inspection_date = diag.date_inspection
        if hasattr(inspection_date, "date"):
            inspection_date = inspection_date
        age_days = (now.date() - inspection_date).days
        if age_days > _OBSOLETE_YEARS * 365:
            recs.append(
                SamplingRecommendation(
                    action_type="refresh_diagnostic",
                    priority="medium",
                    impact_score=0.55,
                    description=f"Refresh obsolete diagnostic (>{_OBSOLETE_YEARS} years old)",
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    pollutant=None,
                    rationale=f"Diagnostic from {diag.date_inspection} is over {_OBSOLETE_YEARS} "
                    "years old. Results may no longer reflect current conditions.",
                ),
            )
    return recs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def plan_sampling(
    db: AsyncSession,
    building_id: UUID,
) -> SamplingPlan | None:
    """Analyze a building and produce a prioritized sampling plan.

    Returns None if the building does not exist.
    """
    # 0. Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # 1. Refresh unknowns (idempotent)
    await unknown_generator.generate_unknowns(db, building_id)

    # 2. Load all open unknowns
    open_result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            ),
        ),
    )
    open_unknowns = list(open_result.scalars().all())

    # 3. Load zones (with elements) for coverage gap analysis
    zone_result = await db.execute(
        select(Zone).options(selectinload(Zone.elements)).where(Zone.building_id == building_id),
    )
    zones = list(zone_result.scalars().all())

    # 4. Load diagnostics for obsolescence check
    diag_result = await db.execute(
        select(Diagnostic).where(Diagnostic.building_id == building_id),
    )
    diagnostics = list(diag_result.scalars().all())

    # 5. Build recommendations from unknowns
    recommendations: list[SamplingRecommendation] = []
    entity_ids_covered: set[UUID] = set()

    for unknown in open_unknowns:
        rec = _build_recommendation_from_unknown(unknown)
        recommendations.append(rec)
        if unknown.entity_id:
            entity_ids_covered.add(unknown.entity_id)

    # 6. Add zone coverage recommendations (sample_zone, beyond what unknowns cover)
    zone_recs = _build_zone_coverage_recommendations(zones, entity_ids_covered)
    recommendations.extend(zone_recs)

    # 7. Add obsolete diagnostic recommendations
    diag_recs = _build_obsolete_diagnostic_recommendations(diagnostics, entity_ids_covered)
    recommendations.extend(diag_recs)

    # 8. Sort by impact_score descending
    recommendations.sort(key=lambda r: r.impact_score, reverse=True)

    # 9. Compute priority breakdown
    priority_breakdown: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for rec in recommendations:
        priority_breakdown[rec.priority] = priority_breakdown.get(rec.priority, 0) + 1

    # 10. Identify coverage gaps (zones with no elements)
    coverage_gaps: list[str] = [str(z.id) for z in zones if not z.elements]

    # 11. Estimate completeness after addressing all recommendations
    completeness_result = await completeness_engine.evaluate_completeness(db, building_id)
    current_score = completeness_result.overall_score

    # Heuristic: each recommendation contributes proportionally to gap closure
    total_impact = sum(r.impact_score for r in recommendations)
    gap = 1.0 - current_score
    estimated_gain = min(gap, gap * min(total_impact / max(len(recommendations) * 0.5, 1.0), 1.0))
    estimated_completeness_after = round(min(1.0, current_score + estimated_gain), 2)

    return SamplingPlan(
        building_id=building_id,
        total_recommendations=len(recommendations),
        recommendations=recommendations,
        estimated_completeness_after=estimated_completeness_after,
        priority_breakdown=priority_breakdown,
        coverage_gaps=coverage_gaps,
        planned_at=datetime.now(UTC),
    )
