"""
SwissBuildingOS - Occupant Safety Evaluator Service

Evaluates occupant exposure risk based on pollutants, material state,
zone usage, and Swiss regulatory thresholds.

Swiss regulatory logic:
- Friable asbestos in habitable zone -> danger
- Radon > 300 Bq/m3 in occupied basement -> warning
- PCB in window joints -> caution (contact exposure)
- Lead paint accessible < 1.5m -> danger if children
- HAP in exterior waterproofing -> safe (no direct exposure)
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.occupant_safety import (
    BuildingExposureRisk,
    BuildingSafetyRecommendations,
    BuildingSafetySummary,
    ExposurePathway,
    OccupantSafetyAssessment,
    PopulationType,
    PortfolioSafetyOverview,
    RecommendationUrgency,
    SafetyLevel,
    SafetyRecommendation,
    ZoneExposureRisk,
    ZonePollutantExposure,
    ZoneSafetyAssessment,
)

# Zone types considered habitable (occupants spend extended time)
_HABITABLE_ZONE_TYPES = {"floor", "room", "staircase"}
# Zone types considered technical (limited occupant access)
_TECHNICAL_ZONE_TYPES = {"technical_room", "parking", "basement"}

# Friable material states that indicate airborne risk
_FRIABLE_STATES = {"friable", "friable_damaged", "degraded", "damaged"}


def _is_habitable(zone_type: str) -> bool:
    return zone_type in _HABITABLE_ZONE_TYPES


def _is_basement(zone_type: str, floor_number: int | None) -> bool:
    if zone_type == "basement":
        return True
    return floor_number is not None and floor_number < 0


def _get_exposure_pathways(pollutant_type: str | None, material_state: str | None) -> list[ExposurePathway]:
    """Determine exposure pathways based on pollutant type and material state."""
    if not pollutant_type:
        return []

    pathways: list[ExposurePathway] = []
    pt = pollutant_type.lower()
    state = (material_state or "").lower()

    if pt == "asbestos":
        if state in _FRIABLE_STATES:
            pathways.append(ExposurePathway.inhalation)
        else:
            pathways.append(ExposurePathway.inhalation)
    elif pt == "radon":
        pathways.append(ExposurePathway.inhalation)
    elif pt == "pcb":
        pathways.append(ExposurePathway.contact)
        pathways.append(ExposurePathway.inhalation)
    elif pt == "lead":
        pathways.append(ExposurePathway.ingestion)
        pathways.append(ExposurePathway.contact)
    elif pt == "hap":
        pathways.append(ExposurePathway.contact)
        pathways.append(ExposurePathway.inhalation)

    return pathways


def _get_exposed_populations(
    zone_type: str,
    pollutant_type: str | None,
    building_type: str | None,
) -> list[PopulationType]:
    """Determine who is exposed based on zone and building type."""
    populations: list[PopulationType] = []

    if _is_habitable(zone_type):
        populations.append(PopulationType.residents)
        if building_type in ("residential", "mixed"):
            populations.append(PopulationType.children)
    elif zone_type in _TECHNICAL_ZONE_TYPES:
        populations.append(PopulationType.workers)
    else:
        populations.append(PopulationType.visitors)

    return populations


def _estimate_daily_hours(zone_type: str) -> float:
    """Estimate daily exposure hours based on zone type."""
    if zone_type in ("room", "floor"):
        return 8.0
    if zone_type == "staircase":
        return 0.5
    if zone_type in ("basement", "parking"):
        return 1.0
    if zone_type == "technical_room":
        return 2.0
    return 0.5


def _evaluate_pollutant_safety(
    pollutant_type: str | None,
    material_state: str | None,
    concentration: float | None,
    zone_type: str,
    floor_number: int | None,
    building_type: str | None,
    material_description: str | None,
) -> tuple[SafetyLevel, str]:
    """
    Evaluate safety level for a single pollutant occurrence.
    Returns (safety_level, detail_string).

    Swiss regulatory logic applied here.
    """
    if not pollutant_type:
        return SafetyLevel.safe, "No pollutant identified"

    pt = pollutant_type.lower()
    state = (material_state or "").lower()
    mat_desc = (material_description or "").lower()
    habitable = _is_habitable(zone_type)
    basement = _is_basement(zone_type, floor_number)
    residential = building_type in ("residential", "mixed")

    # Friable asbestos in habitable zone -> danger
    if pt == "asbestos":
        if state in _FRIABLE_STATES and habitable:
            return SafetyLevel.danger, "Amiante friable en zone habitable - danger immediat"
        if state in _FRIABLE_STATES:
            return SafetyLevel.warning, "Amiante friable en zone technique"
        if habitable:
            return SafetyLevel.caution, "Amiante non-friable en zone habitable"
        return SafetyLevel.safe, "Amiante encapsule en zone technique"

    # Radon > 300 Bq/m3 in occupied basement -> warning
    if pt == "radon":
        if concentration is not None and concentration > 1000:
            return SafetyLevel.danger, f"Radon {concentration} Bq/m3 - largement au-dessus du seuil"
        if concentration is not None and concentration > 300:
            if basement or habitable:
                return SafetyLevel.warning, f"Radon {concentration} Bq/m3 en zone occupee"
            return SafetyLevel.caution, f"Radon {concentration} Bq/m3 en zone non-occupee"
        return SafetyLevel.safe, "Radon sous le seuil de reference"

    # PCB in window joints -> caution
    if pt == "pcb":
        if "joint" in mat_desc or "fenetre" in mat_desc or "window" in mat_desc:
            return SafetyLevel.caution, "PCB dans joints de fenetre - exposition par contact"
        if concentration is not None and concentration > 50:
            if habitable:
                return SafetyLevel.warning, f"PCB {concentration} mg/kg en zone habitable"
            return SafetyLevel.caution, f"PCB {concentration} mg/kg au-dessus du seuil"
        return SafetyLevel.safe, "PCB sous le seuil reglementaire"

    # Lead in accessible paint -> danger if children
    if pt == "lead":
        if concentration is not None and concentration > 5000:
            if residential and habitable:
                return SafetyLevel.danger, "Plomb dans peinture accessible - danger pour enfants"
            if habitable:
                return SafetyLevel.warning, "Plomb au-dessus du seuil en zone habitable"
            return SafetyLevel.caution, "Plomb au-dessus du seuil en zone technique"
        return SafetyLevel.safe, "Plomb sous le seuil reglementaire"

    # HAP in exterior waterproofing -> safe
    if pt == "hap":
        if "etancheite" in mat_desc or "exterieur" in mat_desc or "exterior" in mat_desc:
            return SafetyLevel.safe, "HAP dans etancheite exterieure - pas d'exposition directe"
        if habitable:
            return SafetyLevel.caution, "HAP en zone habitable"
        return SafetyLevel.safe, "HAP en zone non-habitable"

    return SafetyLevel.safe, f"Polluant {pollutant_type} - evaluation par defaut"


_SAFETY_LEVEL_ORDER = {
    SafetyLevel.safe: 0,
    SafetyLevel.caution: 1,
    SafetyLevel.warning: 2,
    SafetyLevel.danger: 3,
}


def _worst_level(levels: list[SafetyLevel]) -> SafetyLevel:
    """Return the worst (highest risk) safety level from a list."""
    if not levels:
        return SafetyLevel.safe
    return max(levels, key=lambda lvl: _SAFETY_LEVEL_ORDER[lvl])


def _level_to_score(level: SafetyLevel) -> float:
    """Convert safety level to a 0-1 score (1 = safe, 0 = danger)."""
    mapping = {
        SafetyLevel.safe: 1.0,
        SafetyLevel.caution: 0.7,
        SafetyLevel.warning: 0.4,
        SafetyLevel.danger: 0.1,
    }
    return mapping[level]


async def _load_building(db: AsyncSession, building_id: UUID) -> Building:
    """Load a building or raise ValueError."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _load_zones_with_materials(db: AsyncSession, building_id: UUID) -> list[Zone]:
    """Load all zones for a building with eager-loaded elements and materials."""
    result = await db.execute(
        select(Zone)
        .where(Zone.building_id == building_id)
        .options(selectinload(Zone.elements).selectinload(BuildingElement.materials))
    )
    return list(result.scalars().all())


async def _load_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Load all samples from diagnostics of a building."""
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


def _collect_pollutant_data(
    zones: list[Zone],
    samples: list[Sample],
) -> dict[UUID, list[dict]]:
    """
    Collect pollutant data per zone from materials and samples.
    Returns {zone_id: [pollutant_info_dict, ...]}.
    """
    zone_pollutants: dict[UUID, list[dict]] = {}

    # From materials linked to zones
    for zone in zones:
        zone_pollutants.setdefault(zone.id, [])
        for element in zone.elements:
            for material in element.materials:
                if material.contains_pollutant and material.pollutant_type:
                    zone_pollutants[zone.id].append(
                        {
                            "pollutant_type": material.pollutant_type,
                            "material_state": material.source,
                            "material_description": material.name,
                            "concentration": None,
                            "unit": None,
                        }
                    )

    # From samples (matched to zones by location)
    for sample in samples:
        if not sample.pollutant_type:
            continue
        # Try to match sample to a zone by floor/room
        matched = False
        for zone in zones:
            if sample.location_floor and zone.name and sample.location_floor.lower() in zone.name.lower():
                zone_pollutants.setdefault(zone.id, []).append(
                    {
                        "pollutant_type": sample.pollutant_type,
                        "material_state": sample.material_state,
                        "material_description": sample.material_description,
                        "concentration": sample.concentration,
                        "unit": sample.unit,
                    }
                )
                matched = True
                break
        if not matched and zones:
            # Assign to first zone as fallback
            first_zone_id = zones[0].id
            zone_pollutants.setdefault(first_zone_id, []).append(
                {
                    "pollutant_type": sample.pollutant_type,
                    "material_state": sample.material_state,
                    "material_description": sample.material_description,
                    "concentration": sample.concentration,
                    "unit": sample.unit,
                }
            )

    return zone_pollutants


async def evaluate_occupant_safety(
    db: AsyncSession,
    building_id: UUID,
) -> OccupantSafetyAssessment:
    """
    Evaluate overall occupant safety for a building.
    Returns a global safety level and per-zone assessments.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_pollutants = _collect_pollutant_data(zones, samples)

    zone_assessments: list[ZoneSafetyAssessment] = []
    all_levels: list[SafetyLevel] = []
    critical_findings: list[str] = []
    zones_at_risk = 0

    for zone in zones:
        pollutants = zone_pollutants.get(zone.id, [])
        zone_levels: list[SafetyLevel] = []
        zone_details: list[str] = []
        dominant_risk: str | None = None

        for p in pollutants:
            level, detail = _evaluate_pollutant_safety(
                pollutant_type=p["pollutant_type"],
                material_state=p["material_state"],
                concentration=p["concentration"],
                zone_type=zone.zone_type,
                floor_number=zone.floor_number,
                building_type=building.building_type,
                material_description=p.get("material_description"),
            )
            zone_levels.append(level)
            zone_details.append(detail)
            if level in (SafetyLevel.danger, SafetyLevel.warning):
                critical_findings.append(f"{zone.name}: {detail}")

        zone_level = _worst_level(zone_levels) if zone_levels else SafetyLevel.safe
        if zone_level in (SafetyLevel.warning, SafetyLevel.danger):
            zones_at_risk += 1

        # Find dominant risk
        if zone_levels:
            worst_idx = max(range(len(zone_levels)), key=lambda i: _SAFETY_LEVEL_ORDER[zone_levels[i]])
            dominant_risk = pollutants[worst_idx]["pollutant_type"] if pollutants else None

        all_levels.append(zone_level)
        zone_assessments.append(
            ZoneSafetyAssessment(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                floor_number=zone.floor_number,
                safety_level=zone_level,
                score=_level_to_score(zone_level),
                pollutant_count=len(pollutants),
                dominant_risk=dominant_risk,
                details=zone_details,
            )
        )

    overall_level = _worst_level(all_levels) if all_levels else SafetyLevel.safe
    overall_score = _level_to_score(overall_level)

    return OccupantSafetyAssessment(
        building_id=building_id,
        overall_safety_level=overall_level,
        overall_score=overall_score,
        zones=zone_assessments,
        total_zones=len(zones),
        zones_at_risk=zones_at_risk,
        critical_findings=critical_findings,
        evaluated_at=datetime.now(UTC),
    )


async def get_exposure_risk_by_zone(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingExposureRisk:
    """
    Get detailed exposure risk per zone: pollutants, pathways,
    populations, and estimated duration.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_pollutants = _collect_pollutant_data(zones, samples)

    zone_risks: list[ZoneExposureRisk] = []
    total_exposures = 0

    for zone in zones:
        pollutants = zone_pollutants.get(zone.id, [])
        exposures: list[ZonePollutantExposure] = []
        zone_levels: list[SafetyLevel] = []

        for p in pollutants:
            pathways = _get_exposure_pathways(p["pollutant_type"], p["material_state"])
            populations = _get_exposed_populations(zone.zone_type, p["pollutant_type"], building.building_type)
            daily_hours = _estimate_daily_hours(zone.zone_type)

            level, _ = _evaluate_pollutant_safety(
                pollutant_type=p["pollutant_type"],
                material_state=p["material_state"],
                concentration=p["concentration"],
                zone_type=zone.zone_type,
                floor_number=zone.floor_number,
                building_type=building.building_type,
                material_description=p.get("material_description"),
            )
            zone_levels.append(level)

            exposures.append(
                ZonePollutantExposure(
                    pollutant_type=p["pollutant_type"],
                    material_state=p["material_state"],
                    concentration=p["concentration"],
                    unit=p.get("unit"),
                    pathways=pathways,
                    exposed_populations=populations,
                    estimated_daily_hours=daily_hours,
                )
            )

        total_exposures += len(exposures)
        zone_risks.append(
            ZoneExposureRisk(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                exposures=exposures,
                overall_risk_level=_worst_level(zone_levels) if zone_levels else SafetyLevel.safe,
                is_habitable_zone=_is_habitable(zone.zone_type),
            )
        )

    return BuildingExposureRisk(
        building_id=building_id,
        zones=zone_risks,
        total_exposures=total_exposures,
        evaluated_at=datetime.now(UTC),
    )


def _generate_zone_recommendations(
    zone: Zone,
    pollutants: list[dict],
    building_type: str | None,
) -> list[SafetyRecommendation]:
    """Generate safety recommendations for a zone based on its pollutants."""
    recommendations: list[SafetyRecommendation] = []

    for p in pollutants:
        level, _ = _evaluate_pollutant_safety(
            pollutant_type=p["pollutant_type"],
            material_state=p["material_state"],
            concentration=p["concentration"],
            zone_type=zone.zone_type,
            floor_number=zone.floor_number,
            building_type=building_type,
            material_description=p.get("material_description"),
        )

        pt = (p["pollutant_type"] or "").lower()
        state = (p["material_state"] or "").lower()

        if level == SafetyLevel.danger:
            # Immediate measures
            recommendations.append(
                SafetyRecommendation(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    urgency=RecommendationUrgency.immediate,
                    category="access_restriction",
                    description=f"Restreindre l'acces a la zone {zone.name} - {pt} detecte",
                    pollutant_type=p["pollutant_type"],
                )
            )
            if pt == "asbestos" and state in _FRIABLE_STATES:
                recommendations.append(
                    SafetyRecommendation(
                        zone_id=zone.id,
                        zone_name=zone.name,
                        urgency=RecommendationUrgency.immediate,
                        category="ventilation",
                        description="Installer ventilation avec filtration HEPA",
                        pollutant_type=p["pollutant_type"],
                        estimated_cost_chf="2000-5000",
                    )
                )
            # Long-term: removal
            recommendations.append(
                SafetyRecommendation(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    urgency=RecommendationUrgency.long_term,
                    category="removal",
                    description=f"Retrait complet du {pt} par entreprise specialisee SUVA",
                    pollutant_type=p["pollutant_type"],
                    estimated_cost_chf="10000-50000",
                )
            )

        elif level == SafetyLevel.warning:
            # Short-term measures
            if pt == "radon":
                recommendations.append(
                    SafetyRecommendation(
                        zone_id=zone.id,
                        zone_name=zone.name,
                        urgency=RecommendationUrgency.short_term,
                        category="ventilation",
                        description="Ameliorer la ventilation du sous-sol - radon au-dessus du seuil",
                        pollutant_type=p["pollutant_type"],
                        estimated_cost_chf="3000-8000",
                    )
                )
            else:
                recommendations.append(
                    SafetyRecommendation(
                        zone_id=zone.id,
                        zone_name=zone.name,
                        urgency=RecommendationUrgency.short_term,
                        category="encapsulation",
                        description=f"Encapsuler le materiau contenant du {pt}",
                        pollutant_type=p["pollutant_type"],
                        estimated_cost_chf="5000-15000",
                    )
                )
            recommendations.append(
                SafetyRecommendation(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    urgency=RecommendationUrgency.short_term,
                    category="signage",
                    description=f"Poser signalisation de danger {pt} dans la zone",
                    pollutant_type=p["pollutant_type"],
                    estimated_cost_chf="100-500",
                )
            )

        elif level == SafetyLevel.caution:
            recommendations.append(
                SafetyRecommendation(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    urgency=RecommendationUrgency.long_term,
                    category="replacement",
                    description=f"Planifier le remplacement des materiaux contenant du {pt}",
                    pollutant_type=p["pollutant_type"],
                    estimated_cost_chf="5000-20000",
                )
            )

    return recommendations


async def generate_safety_recommendations(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingSafetyRecommendations:
    """
    Generate prioritized safety recommendations per zone.
    Immediate, short-term, and long-term measures.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_pollutants = _collect_pollutant_data(zones, samples)

    all_recommendations: list[SafetyRecommendation] = []

    for zone in zones:
        pollutants = zone_pollutants.get(zone.id, [])
        recs = _generate_zone_recommendations(zone, pollutants, building.building_type)
        all_recommendations.extend(recs)

    # Sort by urgency priority
    urgency_order = {
        RecommendationUrgency.immediate: 0,
        RecommendationUrgency.short_term: 1,
        RecommendationUrgency.long_term: 2,
    }
    all_recommendations.sort(key=lambda r: urgency_order[r.urgency])

    immediate = sum(1 for r in all_recommendations if r.urgency == RecommendationUrgency.immediate)
    short_term = sum(1 for r in all_recommendations if r.urgency == RecommendationUrgency.short_term)
    long_term = sum(1 for r in all_recommendations if r.urgency == RecommendationUrgency.long_term)

    return BuildingSafetyRecommendations(
        building_id=building_id,
        recommendations=all_recommendations,
        immediate_count=immediate,
        short_term_count=short_term,
        long_term_count=long_term,
        evaluated_at=datetime.now(UTC),
    )


async def get_portfolio_safety_overview(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioSafetyOverview:
    """
    Portfolio-level safety overview for an organization.
    Shows distribution of safety levels and buildings needing immediate action.
    """
    from app.models.organization import Organization
    from app.services.building_data_loader import load_org_buildings

    # Verify org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise ValueError(f"Organization {org_id} not found")

    # Get buildings created by org members
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioSafetyOverview(
            organization_id=org_id,
            total_buildings=0,
            distribution={"safe": 0, "caution": 0, "warning": 0, "danger": 0},
            buildings_requiring_action=[],
            evaluated_at=datetime.now(UTC),
        )

    distribution: dict[str, int] = {"safe": 0, "caution": 0, "warning": 0, "danger": 0}
    action_buildings: list[BuildingSafetySummary] = []

    for bldg in buildings:
        try:
            assessment = await evaluate_occupant_safety(db, bldg.id)
        except ValueError:
            continue

        level = assessment.overall_safety_level
        distribution[level.value] = distribution.get(level.value, 0) + 1

        requires_action = level in (SafetyLevel.warning, SafetyLevel.danger)
        if requires_action:
            action_buildings.append(
                BuildingSafetySummary(
                    building_id=bldg.id,
                    address=bldg.address,
                    city=bldg.city,
                    safety_level=level,
                    zones_at_risk=assessment.zones_at_risk,
                    requires_immediate_action=level == SafetyLevel.danger,
                )
            )

    # Sort by severity (danger first)
    action_buildings.sort(key=lambda b: _SAFETY_LEVEL_ORDER.get(b.safety_level, 0), reverse=True)

    return PortfolioSafetyOverview(
        organization_id=org_id,
        total_buildings=len(buildings),
        distribution=distribution,
        buildings_requiring_action=action_buildings,
        evaluated_at=datetime.now(UTC),
    )
