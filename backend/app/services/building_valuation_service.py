"""
SwissBuildingOS - Building Valuation Service

Estimates the impact of pollutant findings on Swiss building valuation,
including remediation costs, renovation ROI, market position comparison,
and portfolio-level valuation summaries.
Uses Swiss regulatory context (OTConst, CFST 6503, ORRChim, ORaP).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.building_valuation import (
    AffectedArea,
    BuildingsByImpact,
    MarketPositionResponse,
    PollutantImpactResponse,
    PortfolioValuationSummary,
    PriorityBuilding,
    RenovationROIResponse,
    RiskReduction,
)

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

_RADON_FIXED = 5000.0

# Value reduction percentages per pollutant when threshold exceeded
_VALUE_REDUCTION_PCT: dict[str, float] = {
    "asbestos": 12.0,
    "pcb": 8.0,
    "lead": 4.0,
    "hap": 4.0,
    "radon": 2.0,
}

# Severity multiplier for value reduction
_SEVERITY_MULTIPLIER: dict[str, float] = {
    "critical": 2.0,
    "high": 1.5,
    "medium": 1.0,
    "low": 0.5,
    "unknown": 0.7,
}

# Value increase factor: remediation recovers this fraction of reduced value
_VALUE_RECOVERY_FACTOR = 0.85

# Certifications that become available after full remediation
_CERTIFICATIONS = [
    "Minergie-compliant renovation",
    "Swiss Safe Building label",
    "CECB energy certificate eligibility",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _fetch_samples_grouped(db: AsyncSession, building_id: UUID) -> dict[str, list[Sample]]:
    """Return samples grouped by pollutant_type for completed/validated diagnostics."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    samples = result.scalars().all()
    grouped: dict[str, list[Sample]] = {}
    for s in samples:
        pt = s.pollutant_type
        if pt:
            grouped.setdefault(pt, []).append(s)
    return grouped


def _surface(building: Building) -> float:
    return building.surface_area_m2 or 200.0


def _dominant_risk_level(samples: list[Sample]) -> str:
    priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    best = "unknown"
    best_p = 0
    for s in samples:
        rl = s.risk_level or "unknown"
        if priority.get(rl, 0) > best_p:
            best = rl
            best_p = priority[rl]
    return best


def _has_threshold_exceeded(samples: list[Sample]) -> bool:
    return any(s.threshold_exceeded for s in samples)


def _compute_remediation_cost(pollutant: str, surface: float) -> float:
    rate = _REMEDIATION_COST_PER_M2.get(pollutant, 100.0)
    if pollutant == "radon":
        return _RADON_FIXED + rate * surface
    return rate * surface


def _market_impact_assessment(value_reduction_pct: float) -> str:
    """Classify overall market impact from value reduction percentage."""
    if value_reduction_pct >= 20.0:
        return "severe"
    if value_reduction_pct >= 10.0:
        return "significant"
    if value_reduction_pct >= 5.0:
        return "moderate"
    return "minor"


# ---------------------------------------------------------------------------
# FN1 — estimate_pollutant_impact
# ---------------------------------------------------------------------------


async def estimate_pollutant_impact(db: AsyncSession, building_id: UUID) -> PollutantImpactResponse:
    """Estimate the impact of pollutants on building valuation."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_grouped(db, building_id)
    surface = _surface(building)

    total_cost = 0.0
    total_reduction = 0.0
    affected_areas: list[AffectedArea] = []

    for pollutant, samples in grouped.items():
        if not _has_threshold_exceeded(samples):
            continue

        risk_level = _dominant_risk_level(samples)
        cost = _compute_remediation_cost(pollutant, surface)
        total_cost += cost

        # Value reduction scaled by severity
        base_reduction = _VALUE_REDUCTION_PCT.get(pollutant, 2.0)
        multiplier = _SEVERITY_MULTIPLIER.get(risk_level, 1.0)
        total_reduction += base_reduction * multiplier

        # Build affected areas from sample locations
        for s in samples:
            if s.threshold_exceeded:
                zone = s.location_floor or s.location_room or "unknown"
                affected_areas.append(
                    AffectedArea(
                        zone=zone,
                        pollutant=pollutant,
                        severity=s.risk_level or "unknown",
                    )
                )

    # Cap value reduction at 50%
    total_reduction = min(total_reduction, 50.0)
    impact = _market_impact_assessment(total_reduction)

    return PollutantImpactResponse(
        building_id=building_id,
        estimated_remediation_cost=round(total_cost, 2),
        value_reduction_percentage=round(total_reduction, 2),
        affected_areas=affected_areas,
        market_impact_assessment=impact,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2 — calculate_renovation_roi
# ---------------------------------------------------------------------------


async def calculate_renovation_roi(db: AsyncSession, building_id: UUID) -> RenovationROIResponse:
    """Calculate ROI of remediating all pollutants in a building."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_grouped(db, building_id)
    surface = _surface(building)

    total_cost = 0.0
    total_reduction = 0.0
    worst_before = "low"
    has_exceeded = False
    priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    worst_p = 0

    for pollutant, samples in grouped.items():
        if not _has_threshold_exceeded(samples):
            continue

        has_exceeded = True
        risk_level = _dominant_risk_level(samples)
        cost = _compute_remediation_cost(pollutant, surface)
        total_cost += cost

        base_reduction = _VALUE_REDUCTION_PCT.get(pollutant, 2.0)
        multiplier = _SEVERITY_MULTIPLIER.get(risk_level, 1.0)
        total_reduction += base_reduction * multiplier

        if priority_map.get(risk_level, 0) > worst_p:
            worst_before = risk_level
            worst_p = priority_map[risk_level]

    total_reduction = min(total_reduction, 50.0)

    # Value increase = recovery of the lost value
    estimated_value_increase = total_cost * _VALUE_RECOVERY_FACTOR if total_cost > 0 else 0.0

    roi_pct = (estimated_value_increase / total_cost * 100) if total_cost > 0 else 0.0
    payback = (total_cost / estimated_value_increase) if estimated_value_increase > 0 else 0.0

    # After remediation, risk drops to low
    after_level = "low" if has_exceeded else worst_before

    # Certifications gained only if all pollutants remediated
    certs = list(_CERTIFICATIONS) if has_exceeded else []

    return RenovationROIResponse(
        building_id=building_id,
        total_remediation_cost=round(total_cost, 2),
        estimated_value_increase=round(estimated_value_increase, 2),
        roi_percentage=round(roi_pct, 2),
        payback_period_years=round(payback, 2),
        risk_reduction=RiskReduction(before=worst_before, after=after_level),
        certification_eligibility_gained=certs,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3 — compare_market_position
# ---------------------------------------------------------------------------


async def compare_market_position(db: AsyncSession, building_id: UUID) -> MarketPositionResponse:
    """Compare building's pollutant risk profile against similar buildings."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_grouped(db, building_id)

    # Find comparable buildings: same canton and building_type
    canton = building.canton or ""
    building_type = building.building_type or "residential"
    stmt = select(Building).where(
        Building.canton == canton,
        Building.building_type == building_type,
        Building.id != building_id,
    )
    result = await db.execute(stmt)
    comparables = result.scalars().all()
    comparable_count = len(comparables)

    # Compute this building's severity score
    priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}

    def _building_severity(samples_grouped: dict[str, list[Sample]]) -> int:
        score = 0
        for _pollutant, samples in samples_grouped.items():
            if _has_threshold_exceeded(samples):
                rl = _dominant_risk_level(samples)
                score += priority_map.get(rl, 0)
        return score

    own_severity = _building_severity(grouped)

    # Compute severity for each comparable
    comparable_severities: list[int] = []
    for comp in comparables:
        comp_grouped = await _fetch_samples_grouped(db, comp.id)
        comparable_severities.append(_building_severity(comp_grouped))

    # Percentile: how many comparables are worse (higher severity) than this building
    if comparable_severities:
        worse_count = sum(1 for s in comparable_severities if s > own_severity)
        percentile = (worse_count / len(comparable_severities)) * 100
    else:
        percentile = 50.0  # default when no comparables

    # Average risk in area
    all_severities = [*comparable_severities, own_severity]
    avg_sev = sum(all_severities) / len(all_severities)
    if avg_sev >= 8:
        avg_risk = "critical"
    elif avg_sev >= 4:
        avg_risk = "high"
    elif avg_sev >= 2:
        avg_risk = "medium"
    elif avg_sev > 0:
        avg_risk = "low"
    else:
        avg_risk = "unknown"

    # Advantages / disadvantages
    advantages: list[str] = []
    disadvantages: list[str] = []

    exceeded_pollutants = [p for p, s in grouped.items() if _has_threshold_exceeded(s)]
    clean_pollutants = [p for p in ["asbestos", "pcb", "lead", "hap", "radon"] if p not in exceeded_pollutants]

    if not exceeded_pollutants:
        advantages.append("No pollutant thresholds exceeded")
    if "asbestos" in clean_pollutants:
        advantages.append("Asbestos-free status confirmed")
    if "radon" in clean_pollutants:
        advantages.append("Radon levels within safe limits")

    for p in exceeded_pollutants:
        rl = _dominant_risk_level(grouped[p])
        disadvantages.append(f"{p.upper()} detected at {rl} risk level")

    if percentile >= 75:
        advantages.append("Better than 75% of comparable buildings")
    elif percentile <= 25:
        disadvantages.append("Worse than 75% of comparable buildings")

    return MarketPositionResponse(
        building_id=building_id,
        percentile_rank=round(percentile, 1),
        advantages=advantages,
        disadvantages=disadvantages,
        comparable_buildings_count=comparable_count,
        average_risk_in_area=avg_risk,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_valuation_summary
# ---------------------------------------------------------------------------


async def get_portfolio_valuation_summary(db: AsyncSession, org_id: UUID) -> PortfolioValuationSummary:
    """Organization-wide valuation impact summary."""
    # Verify org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if org is None:
        raise ValueError(f"Organization {org_id} not found")

    # Find buildings created by org members
    from app.services.building_data_loader import load_org_buildings

    empty = PortfolioValuationSummary(
        organization_id=org_id,
        total_remediation_liability=0.0,
        average_value_impact_pct=0.0,
        buildings_by_impact=BuildingsByImpact(),
        top_priority_buildings=[],
        generated_at=datetime.now(UTC),
    )

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return empty

    total_liability = 0.0
    impact_counts = {"minor": 0, "moderate": 0, "significant": 0, "severe": 0}
    building_impacts: list[tuple[float, float, str, Building]] = []  # (cost, reduction, impact, building)

    for bldg in buildings:
        grouped = await _fetch_samples_grouped(db, bldg.id)
        surface = _surface(bldg)

        cost = 0.0
        reduction = 0.0

        for pollutant, samples in grouped.items():
            if _has_threshold_exceeded(samples):
                cost += _compute_remediation_cost(pollutant, surface)
                risk_level = _dominant_risk_level(samples)
                base_red = _VALUE_REDUCTION_PCT.get(pollutant, 2.0)
                mult = _SEVERITY_MULTIPLIER.get(risk_level, 1.0)
                reduction += base_red * mult

        reduction = min(reduction, 50.0)
        impact = _market_impact_assessment(reduction)
        impact_counts[impact] = impact_counts.get(impact, 0) + 1
        total_liability += cost
        building_impacts.append((cost, reduction, impact, bldg))

    # Average value impact
    total_reduction = sum(bi[1] for bi in building_impacts)
    avg_impact = total_reduction / len(building_impacts) if building_impacts else 0.0

    # Top priority: sort by cost descending, take top 5
    building_impacts.sort(key=lambda x: x[0], reverse=True)
    top_priority = [
        PriorityBuilding(
            building_id=bldg.id,
            address=bldg.address or "",
            remediation_cost=round(cost, 2),
            value_impact_pct=round(reduction, 2),
            market_impact=impact,
        )
        for cost, reduction, impact, bldg in building_impacts[:5]
        if cost > 0
    ]

    return PortfolioValuationSummary(
        organization_id=org_id,
        total_remediation_liability=round(total_liability, 2),
        average_value_impact_pct=round(avg_impact, 2),
        buildings_by_impact=BuildingsByImpact(**impact_counts),
        top_priority_buildings=top_priority,
        generated_at=datetime.now(UTC),
    )
