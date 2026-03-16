"""
SwissBuildingOS - Environmental Impact Service

Assesses environmental risks from building pollutants, estimates the
environmental footprint of remediation works, computes a composite green
building score, and aggregates portfolio-level environmental reports.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.environmental_impact import (
    BuildingGreenSummary,
    EmissionDetail,
    EnvironmentalImpactAssessment,
    GreenBuildingScore,
    GreenScoreSubCategory,
    ImprovementOpportunity,
    PortfolioEnvironmentalReport,
    RemediationFootprint,
    RiskCategory,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_POLLUTANT_SOIL_WEIGHT: dict[str, float] = {
    "asbestos": 0.6,
    "pcb": 0.9,
    "lead": 0.8,
    "hap": 0.7,
    "radon": 0.1,
}

_POLLUTANT_WATER_WEIGHT: dict[str, float] = {
    "asbestos": 0.2,
    "pcb": 0.8,
    "lead": 0.9,
    "hap": 0.6,
    "radon": 0.05,
}

_POLLUTANT_AIR_WEIGHT: dict[str, float] = {
    "asbestos": 0.9,
    "pcb": 0.3,
    "lead": 0.2,
    "hap": 0.5,
    "radon": 0.8,
}

_POLLUTANT_NEIGHBORHOOD_WEIGHT: dict[str, float] = {
    "asbestos": 0.7,
    "pcb": 0.4,
    "lead": 0.3,
    "hap": 0.4,
    "radon": 0.6,
}

_CO2_PER_TONNE_WASTE_TRANSPORT_KG = 25.0  # kg CO2 per tonne-km, ~50 km avg
_CO2_PER_TONNE_DISPOSAL_KG = 80.0  # kg CO2 per tonne incinerated/landfilled
_WASTE_KG_PER_SAMPLE_POSITIVE = 200.0  # rough estimate of waste per positive sample


def _level_from_score(score: float) -> str:
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def _grade_from_score(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "E"


def _energy_class_score(construction_year: int | None) -> float:
    """Heuristic energy score from construction year (0-100)."""
    if construction_year is None:
        return 30.0
    if construction_year >= 2010:
        return 90.0
    if construction_year >= 2000:
        return 70.0
    if construction_year >= 1990:
        return 55.0
    if construction_year >= 1975:
        return 40.0
    if construction_year >= 1960:
        return 30.0
    return 25.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_positive_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Return samples with threshold_exceeded=True for the building."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(Diagnostic.building_id == building_id, Sample.threshold_exceeded.is_(True))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_all_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(Diagnostic.building_id == building_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_completed_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    stmt = select(Intervention).where(
        Intervention.building_id == building_id,
        Intervention.status == "completed",
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _compute_category_score(
    positive_pollutants: set[str],
    weight_map: dict[str, float],
    building_type: str,
) -> float:
    """Weighted score for a risk category based on detected pollutants."""
    if not positive_pollutants:
        return 0.0
    total_weight = 0.0
    for pollutant in positive_pollutants:
        w = weight_map.get(pollutant, 0.3)
        total_weight += w
    # Normalize by max possible (5 pollutants)
    raw = total_weight / 5.0
    # Building type modifier
    if building_type in ("industrial", "commercial"):
        raw *= 1.2
    return min(raw, 1.0)


def _justification_for_category(
    category_name: str,
    positive_pollutants: set[str],
    level: str,
) -> str:
    if not positive_pollutants:
        return f"No detected pollutants affecting {category_name}."
    pollutant_list = ", ".join(sorted(positive_pollutants))
    return f"{level.capitalize()} {category_name} risk due to detected: {pollutant_list}."


# ---------------------------------------------------------------------------
# FN1: assess_environmental_impact
# ---------------------------------------------------------------------------


async def assess_environmental_impact(
    db: AsyncSession,
    building_id: UUID,
) -> EnvironmentalImpactAssessment:
    """Assess environmental risk from building pollutants across 4 categories."""
    building = await _get_building(db, building_id)
    positive_samples = await _get_positive_samples(db, building_id)

    detected: set[str] = set()
    for s in positive_samples:
        pt = (s.pollutant_type or "").lower()
        if pt:
            detected.add(pt)

    building_type = (building.building_type or "residential").lower()

    # Compute each category
    categories = []
    for cat_name, weight_map in [
        ("soil_contamination", _POLLUTANT_SOIL_WEIGHT),
        ("water_table_risk", _POLLUTANT_WATER_WEIGHT),
        ("air_quality_impact", _POLLUTANT_AIR_WEIGHT),
        ("neighborhood_exposure", _POLLUTANT_NEIGHBORHOOD_WEIGHT),
    ]:
        score = _compute_category_score(detected, weight_map, building_type)
        level = _level_from_score(score)
        justification = _justification_for_category(cat_name, detected, level)
        categories.append(
            RiskCategory(
                category=cat_name,
                level=level,
                score=round(score, 4),
                justification=justification,
            )
        )

    max_level = max(c.score for c in categories) if categories else 0.0
    overall = _level_from_score(max_level)

    return EnvironmentalImpactAssessment(
        building_id=building_id,
        soil_contamination=categories[0],
        water_table_risk=categories[1],
        air_quality_impact=categories[2],
        neighborhood_exposure=categories[3],
        overall_level=overall,
        assessed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: estimate_remediation_environmental_footprint
# ---------------------------------------------------------------------------


async def estimate_remediation_environmental_footprint(
    db: AsyncSession,
    building_id: UUID,
) -> RemediationFootprint:
    """Estimate the environmental cost of remediation for a building."""
    building = await _get_building(db, building_id)
    positive_samples = await _get_positive_samples(db, building_id)

    n_positive = len(positive_samples)
    surface_m2 = building.surface_area_m2 or 200.0

    # Waste estimate
    waste_tonnes = (n_positive * _WASTE_KG_PER_SAMPLE_POSITIVE) / 1000.0
    transport_co2 = waste_tonnes * _CO2_PER_TONNE_WASTE_TRANSPORT_KG
    disposal_co2 = waste_tonnes * _CO2_PER_TONNE_DISPOSAL_KG

    # Dust/fiber release risk
    detected_pollutants = {(s.pollutant_type or "").lower() for s in positive_samples}
    if "asbestos" in detected_pollutants:
        dust_risk = "high"
    elif detected_pollutants & {"lead", "hap"}:
        dust_risk = "medium"
    else:
        dust_risk = "low"

    # Temporary contamination risk
    if n_positive >= 5:
        temp_risk = "high"
    elif n_positive >= 2:
        temp_risk = "medium"
    else:
        temp_risk = "low"

    total_co2 = transport_co2 + disposal_co2

    # Long-term avoided emissions (health + environmental degradation proxy)
    avoided_co2 = n_positive * 50.0 + surface_m2 * 0.5

    net_balance = avoided_co2 - total_co2

    details = [
        EmissionDetail(
            source="waste_transport",
            co2_kg=round(transport_co2, 2),
            description=f"Transport of {waste_tonnes:.2f} tonnes of contaminated waste",
        ),
        EmissionDetail(
            source="waste_disposal",
            co2_kg=round(disposal_co2, 2),
            description=f"Incineration/landfill of {waste_tonnes:.2f} tonnes",
        ),
    ]

    return RemediationFootprint(
        building_id=building_id,
        waste_transport_co2_kg=round(transport_co2, 2),
        disposal_emissions_co2_kg=round(disposal_co2, 2),
        dust_fiber_release_risk=dust_risk,
        temporary_contamination_risk=temp_risk,
        total_remediation_co2_kg=round(total_co2, 2),
        avoided_long_term_co2_kg=round(avoided_co2, 2),
        net_environmental_balance_co2_kg=round(net_balance, 2),
        emission_details=details,
        estimated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: calculate_green_building_score
# ---------------------------------------------------------------------------


async def calculate_green_building_score(
    db: AsyncSession,
    building_id: UUID,
) -> GreenBuildingScore:
    """Compute a composite green building score (0-100)."""
    building = await _get_building(db, building_id)
    all_samples = await _get_all_samples(db, building_id)
    positive_samples = [s for s in all_samples if s.threshold_exceeded]
    completed_interventions = await _get_completed_interventions(db, building_id)

    # Sub-category 1: Pollutant-free status (weight 0.35)
    if not all_samples:
        pollutant_score = 50.0  # unknown
    elif not positive_samples:
        pollutant_score = 100.0  # clean
    else:
        ratio = len(positive_samples) / len(all_samples)
        pollutant_score = max(0.0, (1.0 - ratio) * 80.0)

    # Sub-category 2: Energy class heuristic (weight 0.25)
    energy_score = _energy_class_score(building.construction_year)

    # Sub-category 3: Completed remediations (weight 0.25)
    remediation_types = {"decontamination", "asbestos_removal", "remediation", "encapsulation"}
    remediation_interventions = [
        i for i in completed_interventions if (i.intervention_type or "").lower() in remediation_types
    ]
    if positive_samples and remediation_interventions:
        remediation_ratio = min(len(remediation_interventions) / max(len(positive_samples), 1), 1.0)
        remediation_score = remediation_ratio * 100.0
    elif not positive_samples:
        remediation_score = 100.0  # nothing to remediate
    else:
        remediation_score = 0.0

    # Sub-category 4: Monitoring compliance (weight 0.15)
    has_diagnostics = len(all_samples) > 0
    recent_intervention = any(True for i in completed_interventions if i.date_end is not None)
    monitoring_score = 0.0
    if has_diagnostics:
        monitoring_score += 60.0
    if recent_intervention:
        monitoring_score += 40.0

    # Weighted total
    weights = [0.35, 0.25, 0.25, 0.15]
    scores = [pollutant_score, energy_score, remediation_score, monitoring_score]
    overall = sum(w * s for w, s in zip(weights, scores, strict=True))
    overall = round(min(overall, 100.0), 1)

    sub_categories = [
        GreenScoreSubCategory(
            name="pollutant_free_status",
            score=round(pollutant_score, 1),
            weight=0.35,
            details="Based on ratio of clean vs. contaminated samples",
        ),
        GreenScoreSubCategory(
            name="energy_class",
            score=round(energy_score, 1),
            weight=0.25,
            details=f"Estimated from construction year ({building.construction_year})",
        ),
        GreenScoreSubCategory(
            name="completed_remediations",
            score=round(remediation_score, 1),
            weight=0.25,
            details=f"{len(remediation_interventions)} remediation(s) completed",
        ),
        GreenScoreSubCategory(
            name="monitoring_compliance",
            score=round(monitoring_score, 1),
            weight=0.15,
            details="Diagnostic records and recent interventions",
        ),
    ]

    recommendations: list[str] = []
    if pollutant_score < 60:
        recommendations.append("Schedule remediation for detected pollutants")
    if energy_score < 50:
        recommendations.append("Consider energy renovation to improve building envelope")
    if remediation_score < 50 and positive_samples:
        recommendations.append("Complete pending pollutant remediation works")
    if monitoring_score < 50:
        recommendations.append("Establish regular diagnostic monitoring program")

    return GreenBuildingScore(
        building_id=building_id,
        overall_score=overall,
        grade=_grade_from_score(overall),
        sub_categories=sub_categories,
        recommendations=recommendations,
        scored_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_environmental_report
# ---------------------------------------------------------------------------


async def get_portfolio_environmental_report(
    db: AsyncSession,
    org_id: UUID | None,
) -> PortfolioEnvironmentalReport:
    """Generate an organization-level environmental report."""
    # Fetch buildings
    if org_id is not None:
        buildings = await load_org_buildings(db, org_id)
    else:
        result = await db.execute(select(Building))
        buildings = list(result.scalars().all())

    total_buildings = len(buildings)
    if total_buildings == 0:
        return PortfolioEnvironmentalReport(
            org_id=org_id,
            total_buildings=0,
            total_environmental_footprint_co2_kg=0.0,
            avg_green_score=0.0,
            grade_distribution={},
            top_performers=[],
            worst_performers=[],
            improvement_opportunities=[],
            regulatory_compliance_rate=0.0,
            generated_at=datetime.now(UTC),
        )

    # Calculate green score + footprint for each building
    scored: list[tuple[Building, GreenBuildingScore, float]] = []
    total_co2 = 0.0
    grade_dist: dict[str, int] = {}
    compliant_count = 0

    for b in buildings:
        gs = await calculate_green_building_score(db, b.id)
        fp = await estimate_remediation_environmental_footprint(db, b.id)
        total_co2 += fp.total_remediation_co2_kg
        grade_dist[gs.grade] = grade_dist.get(gs.grade, 0) + 1
        if gs.overall_score >= 50:
            compliant_count += 1
        scored.append((b, gs, fp.total_remediation_co2_kg))

    scored.sort(key=lambda x: x[1].overall_score, reverse=True)
    avg_score = sum(s[1].overall_score for s in scored) / total_buildings

    top = [
        BuildingGreenSummary(
            building_id=b.id,
            address=b.address,
            overall_score=gs.overall_score,
            grade=gs.grade,
        )
        for b, gs, _ in scored[:5]
    ]

    worst = [
        BuildingGreenSummary(
            building_id=b.id,
            address=b.address,
            overall_score=gs.overall_score,
            grade=gs.grade,
        )
        for b, gs, _ in scored[-5:]
    ]

    # Improvement opportunities: buildings with score < 50
    opportunities = [
        ImprovementOpportunity(
            building_id=b.id,
            address=b.address,
            current_score=gs.overall_score,
            potential_score=min(gs.overall_score + 30.0, 100.0),
            action="Remediate pollutants and improve monitoring",
        )
        for b, gs, _ in scored
        if gs.overall_score < 50
    ][:10]

    compliance_rate = (compliant_count / total_buildings) * 100.0 if total_buildings else 0.0

    return PortfolioEnvironmentalReport(
        org_id=org_id,
        total_buildings=total_buildings,
        total_environmental_footprint_co2_kg=round(total_co2, 2),
        avg_green_score=round(avg_score, 1),
        grade_distribution=grade_dist,
        top_performers=top,
        worst_performers=worst,
        improvement_opportunities=opportunities,
        regulatory_compliance_rate=round(compliance_rate, 1),
        generated_at=datetime.now(UTC),
    )
