"""
SwissBuildingOS - Occupancy Risk Service

Assesses occupant exposure risk during renovation works.
Evaluates relocation needs, generates communication plans,
and provides portfolio-level occupancy risk overviews.

Swiss regulatory basis:
- OTConst Art. 60a, 82-86 (asbestos work categories)
- CFST 6503 (minor/medium/major intervention thresholds)
- ORRChim Annexe 2.15 (PCB > 50 mg/kg)
- ORaP Art. 110 (radon 300/1000 Bq/m3)
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
from app.schemas.occupancy_risk import (
    AffectedUnit,
    CommunicationPhase,
    CostEstimateRange,
    HighPriorityBuilding,
    KeyMessage,
    OccupancyRiskAssessment,
    OccupancyRiskFactor,
    OccupancyRiskLevel,
    OccupantCommunicationPlan,
    PortfolioOccupancyRisk,
    RelocationUrgency,
    TemporaryRelocationAssessment,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HABITABLE_ZONE_TYPES = {"floor", "room", "staircase"}
_FRIABLE_STATES = {"friable", "friable_damaged", "degraded", "damaged"}

# Canton → primary language(s)
_CANTON_LANGUAGES: dict[str, list[str]] = {
    "VD": ["FR"],
    "GE": ["FR"],
    "NE": ["FR"],
    "JU": ["FR"],
    "FR": ["FR", "DE"],
    "VS": ["FR", "DE"],
    "BE": ["DE", "FR"],
    "ZH": ["DE"],
    "AG": ["DE"],
    "BS": ["DE"],
    "BL": ["DE"],
    "LU": ["DE"],
    "SG": ["DE"],
    "TG": ["DE"],
    "SO": ["DE"],
    "SZ": ["DE"],
    "ZG": ["DE"],
    "AR": ["DE"],
    "AI": ["DE"],
    "GL": ["DE"],
    "GR": ["DE", "IT"],
    "NW": ["DE"],
    "OW": ["DE"],
    "SH": ["DE"],
    "UR": ["DE"],
    "TI": ["IT"],
}

# Occupant density estimates per building type (persons per floor)
_OCCUPANT_DENSITY = {
    "residential": 4,
    "mixed": 6,
    "commercial": 8,
    "public": 12,
    "industrial": 3,
}

# Cost per person per day for temporary relocation (CHF)
_RELOCATION_COST_PER_PERSON_PER_DAY_MIN = 80.0
_RELOCATION_COST_PER_PERSON_PER_DAY_MAX = 200.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _load_zones(db: AsyncSession, building_id: UUID) -> list[Zone]:
    result = await db.execute(
        select(Zone)
        .where(Zone.building_id == building_id)
        .options(selectinload(Zone.elements).selectinload(BuildingElement.materials))
    )
    return list(result.scalars().all())


async def _load_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


def _estimate_occupant_count(building: Building, zones: list[Zone]) -> int:
    """Estimate occupant count from building metadata and zone count."""
    floors = building.floors_above or 1
    density = _OCCUPANT_DENSITY.get((building.building_type or "residential").lower(), 4)
    # If we have habitable zones, use their count as a better proxy
    habitable_zones = [z for z in zones if z.zone_type in _HABITABLE_ZONE_TYPES]
    if habitable_zones:
        return max(1, len(habitable_zones) * density)
    return max(1, floors * density)


def _evaluate_sample_risk(sample: Sample) -> tuple[OccupancyRiskLevel, str]:
    """Evaluate occupancy risk from a single sample."""
    pt = (sample.pollutant_type or "").lower()
    state = (sample.material_state or "").lower()
    conc = sample.concentration

    if pt == "asbestos":
        if state in _FRIABLE_STATES:
            return OccupancyRiskLevel.critical, "Amiante friable - exposition par inhalation lors de travaux"
        if sample.threshold_exceeded:
            return OccupancyRiskLevel.high, "Amiante confirme - risque lors d'intervention mecanique"
        return OccupancyRiskLevel.medium, "Amiante possible - analyse complementaire requise"

    if pt == "radon":
        if conc is not None and conc > 1000:
            return OccupancyRiskLevel.critical, f"Radon {conc} Bq/m3 - ventilation obligatoire"
        if conc is not None and conc > 300:
            return OccupancyRiskLevel.high, f"Radon {conc} Bq/m3 - au-dessus du seuil de reference"
        return OccupancyRiskLevel.low, "Radon sous le seuil"

    if pt == "pcb":
        if conc is not None and conc > 50:
            return OccupancyRiskLevel.high, f"PCB {conc} mg/kg - decontamination requise"
        return OccupancyRiskLevel.medium, "PCB detecte sous le seuil"

    if pt == "lead":
        if conc is not None and conc > 5000:
            return OccupancyRiskLevel.high, f"Plomb {conc} mg/kg - danger pour occupants"
        return OccupancyRiskLevel.medium, "Plomb detecte sous le seuil"

    if pt == "hap":
        if sample.threshold_exceeded:
            return OccupancyRiskLevel.medium, "HAP au-dessus du seuil"
        return OccupancyRiskLevel.low, "HAP sous le seuil"

    return OccupancyRiskLevel.low, f"Polluant {pt} - risque faible par defaut"


def _evaluate_material_risk(
    pollutant_type: str,
    material_state: str | None,
    zone_type: str,
) -> tuple[OccupancyRiskLevel, str]:
    """Evaluate occupancy risk from a material in a zone."""
    pt = pollutant_type.lower()
    state = (material_state or "").lower()
    habitable = zone_type in _HABITABLE_ZONE_TYPES

    if pt == "asbestos":
        if state in _FRIABLE_STATES and habitable:
            return OccupancyRiskLevel.critical, "Amiante friable en zone habitable"
        if state in _FRIABLE_STATES:
            return OccupancyRiskLevel.high, "Amiante friable en zone technique"
        if habitable:
            return OccupancyRiskLevel.medium, "Amiante non-friable en zone habitable"
        return OccupancyRiskLevel.low, "Amiante encapsule en zone technique"

    if pt == "lead" and habitable:
        return OccupancyRiskLevel.medium, "Plomb en zone habitable"

    if pt == "pcb" and habitable:
        return OccupancyRiskLevel.medium, "PCB en zone habitable"

    return OccupancyRiskLevel.low, f"{pt} - risque faible"


_RISK_ORDER = {
    OccupancyRiskLevel.low: 0,
    OccupancyRiskLevel.medium: 1,
    OccupancyRiskLevel.high: 2,
    OccupancyRiskLevel.critical: 3,
}


def _worst_risk(levels: list[OccupancyRiskLevel]) -> OccupancyRiskLevel:
    if not levels:
        return OccupancyRiskLevel.low
    return max(levels, key=lambda lvl: _RISK_ORDER[lvl])


def _mitigation_for_level(level: OccupancyRiskLevel) -> list[str]:
    """Generate mitigation recommendations based on overall risk level."""
    recs: list[str] = []
    if level == OccupancyRiskLevel.critical:
        recs.append("Evacuation immediate des occupants des zones critiques")
        recs.append("Confinement des zones contaminées avant intervention")
        recs.append("Engagement d'une entreprise SUVA pour desamiantage")
        recs.append("Suivi medical des occupants exposes")
    elif level == OccupancyRiskLevel.high:
        recs.append("Planifier le relogement temporaire des occupants")
        recs.append("Installer des barrieres de confinement")
        recs.append("Ventilation avec filtration HEPA pendant les travaux")
    elif level == OccupancyRiskLevel.medium:
        recs.append("Informer les occupants des travaux prevus")
        recs.append("Planifier les travaux en dehors des heures d'occupation")
        recs.append("Surveiller la qualite de l'air pendant les travaux")
    else:
        recs.append("Mesures de precaution standard suffisantes")
    return recs


# ---------------------------------------------------------------------------
# FN1: assess_occupancy_risk
# ---------------------------------------------------------------------------


async def assess_occupancy_risk(
    building_id: UUID,
    db: AsyncSession,
) -> OccupancyRiskAssessment:
    """
    Assess occupancy risk for a building during renovation.
    Returns risk level, contributing factors, mitigation recommendations,
    and estimated occupant count.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones(db, building_id)
    samples = await _load_samples(db, building_id)

    risk_factors: list[OccupancyRiskFactor] = []
    all_levels: list[OccupancyRiskLevel] = []

    # Evaluate from samples
    for sample in samples:
        level, desc = _evaluate_sample_risk(sample)
        affected = []
        # Match sample to zones
        for zone in zones:
            if sample.location_floor and zone.name and sample.location_floor.lower() in zone.name.lower():
                affected.append(zone.name)
                break
        if not affected and zones:
            affected.append(zones[0].name)

        risk_factors.append(
            OccupancyRiskFactor(
                factor_name=f"sample_{sample.pollutant_type or 'unknown'}",
                severity=level,
                description=desc,
                affected_zones=affected,
            )
        )
        all_levels.append(level)

    # Evaluate from materials in zones
    for zone in zones:
        for element in zone.elements:
            for material in element.materials:
                if material.contains_pollutant and material.pollutant_type:
                    level, desc = _evaluate_material_risk(
                        material.pollutant_type,
                        material.source,
                        zone.zone_type,
                    )
                    risk_factors.append(
                        OccupancyRiskFactor(
                            factor_name=f"material_{material.pollutant_type}",
                            severity=level,
                            description=desc,
                            affected_zones=[zone.name],
                        )
                    )
                    all_levels.append(level)

    overall = _worst_risk(all_levels)
    occupant_count = _estimate_occupant_count(building, zones)
    mitigations = _mitigation_for_level(overall)

    return OccupancyRiskAssessment(
        building_id=building_id,
        risk_level=overall,
        risk_factors=risk_factors,
        mitigation_recommendations=mitigations,
        occupant_count_estimate=occupant_count,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: evaluate_temporary_relocation
# ---------------------------------------------------------------------------


async def evaluate_temporary_relocation(
    building_id: UUID,
    db: AsyncSession,
) -> TemporaryRelocationAssessment:
    """
    Evaluate whether temporary relocation of occupants is needed.
    Returns relocation urgency, duration, affected units, cost estimate,
    and regulatory basis.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones(db, building_id)
    samples = await _load_samples(db, building_id)

    affected_units: list[AffectedUnit] = []
    regulatory_basis: list[str] = []
    worst_level = OccupancyRiskLevel.low
    has_critical = False
    has_high = False

    # Check samples for relocation triggers
    for sample in samples:
        level, desc = _evaluate_sample_risk(sample)
        if _RISK_ORDER[level] > _RISK_ORDER[worst_level]:
            worst_level = level

        if level in (OccupancyRiskLevel.critical, OccupancyRiskLevel.high):
            pt = (sample.pollutant_type or "").lower()
            # Find affected zones
            for zone in zones:
                if zone.zone_type not in _HABITABLE_ZONE_TYPES:
                    continue
                matched = False
                if sample.location_floor and zone.name and sample.location_floor.lower() in zone.name.lower():
                    matched = True
                if matched or not sample.location_floor:
                    already = any(u.zone_id == zone.id for u in affected_units)
                    if not already:
                        affected_units.append(
                            AffectedUnit(
                                zone_id=zone.id,
                                zone_name=zone.name,
                                zone_type=zone.zone_type,
                                floor_number=zone.floor_number,
                                reason=desc,
                            )
                        )

            if level == OccupancyRiskLevel.critical:
                has_critical = True
            else:
                has_high = True

            # Add regulatory basis
            if pt == "asbestos" and "OTConst Art. 60a" not in regulatory_basis:
                regulatory_basis.append("OTConst Art. 60a, 82-86 (amiante)")
                regulatory_basis.append("CFST 6503 (categories de travaux)")
            elif pt == "pcb" and "ORRChim" not in " ".join(regulatory_basis):
                regulatory_basis.append("ORRChim Annexe 2.15 (PCB > 50 mg/kg)")
            elif pt == "lead" and "ORRChim" not in " ".join(regulatory_basis):
                regulatory_basis.append("ORRChim Annexe 2.18 (plomb > 5000 mg/kg)")
            elif pt == "radon" and "ORaP" not in " ".join(regulatory_basis):
                regulatory_basis.append("ORaP Art. 110 (radon 300/1000 Bq/m3)")

    # If no samples but zones have pollutant materials, check those
    if not samples:
        for zone in zones:
            for element in zone.elements:
                for material in element.materials:
                    if material.contains_pollutant and material.pollutant_type:
                        level, desc = _evaluate_material_risk(
                            material.pollutant_type,
                            material.source,
                            zone.zone_type,
                        )
                        if _RISK_ORDER[level] > _RISK_ORDER[worst_level]:
                            worst_level = level
                        if level in (OccupancyRiskLevel.critical, OccupancyRiskLevel.high):
                            if zone.zone_type in _HABITABLE_ZONE_TYPES:
                                already = any(u.zone_id == zone.id for u in affected_units)
                                if not already:
                                    affected_units.append(
                                        AffectedUnit(
                                            zone_id=zone.id,
                                            zone_name=zone.name,
                                            zone_type=zone.zone_type,
                                            floor_number=zone.floor_number,
                                            reason=desc,
                                        )
                                    )
                            if level == OccupancyRiskLevel.critical:
                                has_critical = True
                            else:
                                has_high = True

    relocation_needed = has_critical or has_high
    if has_critical:
        urgency = RelocationUrgency.immediate
    elif has_high:
        urgency = RelocationUrgency.planned
    else:
        urgency = RelocationUrgency.not_required

    # Duration estimate based on severity
    if has_critical:
        duration_days = 30
    elif has_high:
        duration_days = 14
    else:
        duration_days = 0

    # Cost estimate
    affected_occupants = (
        max(1, len(affected_units) * _OCCUPANT_DENSITY.get((building.building_type or "residential").lower(), 4))
        if affected_units
        else 0
    )

    cost_range = CostEstimateRange(
        min_chf=affected_occupants * duration_days * _RELOCATION_COST_PER_PERSON_PER_DAY_MIN,
        max_chf=affected_occupants * duration_days * _RELOCATION_COST_PER_PERSON_PER_DAY_MAX,
    )

    return TemporaryRelocationAssessment(
        building_id=building_id,
        relocation_needed=relocation_needed,
        urgency=urgency,
        estimated_duration_days=duration_days,
        affected_units=affected_units,
        cost_estimate_range=cost_range,
        regulatory_basis=regulatory_basis,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: generate_occupant_communication
# ---------------------------------------------------------------------------


async def generate_occupant_communication(
    building_id: UUID,
    db: AsyncSession,
) -> OccupantCommunicationPlan:
    """
    Generate a structured communication plan for building occupants
    during renovation works involving pollutants.
    """
    building = await _load_building(db, building_id)

    canton = building.canton or ""
    languages = _CANTON_LANGUAGES.get(canton.upper(), ["FR", "DE"])

    # Determine affected parties
    building_type = (building.building_type or "residential").lower()
    affected_parties: list[str] = []
    if building_type in ("residential", "mixed"):
        affected_parties.append("Locataires")
        affected_parties.append("Proprietaires")
    if building_type in ("commercial", "mixed"):
        affected_parties.append("Commercants")
    if building_type == "public":
        affected_parties.append("Usagers du batiment")
    affected_parties.append("Concierge / regie")

    # Assess risk to determine communication intensity
    risk_assessment = await assess_occupancy_risk(building_id, db)
    risk_level = risk_assessment.risk_level

    # Build notification timeline
    timeline: list[str] = []
    if risk_level == OccupancyRiskLevel.critical:
        timeline.append("J-0: Notification immediate d'evacuation")
        timeline.append("J+1: Confirmation ecrite avec instructions detaillees")
        timeline.append("J+3: Point de situation avec autorites cantonales")
        timeline.append("Hebdomadaire: Mise a jour de l'avancement des travaux")
    elif risk_level == OccupancyRiskLevel.high:
        timeline.append("J-30: Premiere information sur les travaux prevus")
        timeline.append("J-14: Details du planning et mesures de protection")
        timeline.append("J-7: Rappel et instructions finales")
        timeline.append("Hebdomadaire: Mise a jour pendant les travaux")
    elif risk_level == OccupancyRiskLevel.medium:
        timeline.append("J-14: Information sur les travaux prevus")
        timeline.append("J-3: Rappel et consignes pratiques")
        timeline.append("Bi-hebdomadaire: Mise a jour pendant les travaux")
    else:
        timeline.append("J-7: Information generale sur les travaux")
        timeline.append("J-1: Rappel")

    # Build key messages per phase
    key_messages: list[KeyMessage] = []

    # BEFORE phase
    if risk_level in (OccupancyRiskLevel.critical, OccupancyRiskLevel.high):
        key_messages.append(
            KeyMessage(
                phase=CommunicationPhase.before,
                message="Des polluants ont ete identifies dans le batiment. "
                "Des travaux d'assainissement sont necessaires pour votre securite.",
                priority=1,
            )
        )
        key_messages.append(
            KeyMessage(
                phase=CommunicationPhase.before,
                message="Un relogement temporaire sera organise pendant la duree des travaux.",
                priority=2,
            )
        )
    else:
        key_messages.append(
            KeyMessage(
                phase=CommunicationPhase.before,
                message="Des travaux de renovation sont planifies. Des mesures de precaution seront mises en place.",
                priority=1,
            )
        )

    # DURING phase
    key_messages.append(
        KeyMessage(
            phase=CommunicationPhase.during,
            message="Les travaux sont en cours. Respectez les consignes de securite affichees.",
            priority=1,
        )
    )
    if risk_level in (OccupancyRiskLevel.critical, OccupancyRiskLevel.high):
        key_messages.append(
            KeyMessage(
                phase=CommunicationPhase.during,
                message="L'acces aux zones de travaux est strictement interdit.",
                priority=2,
            )
        )

    # AFTER phase
    key_messages.append(
        KeyMessage(
            phase=CommunicationPhase.after,
            message="Les travaux sont termines. Les analyses de controle confirment la conformite des zones assainies.",
            priority=1,
        )
    )
    if risk_level in (OccupancyRiskLevel.critical, OccupancyRiskLevel.high):
        key_messages.append(
            KeyMessage(
                phase=CommunicationPhase.after,
                message="Le retour dans les logements est autorise. Un rapport de controle est disponible sur demande.",
                priority=2,
            )
        )

    return OccupantCommunicationPlan(
        building_id=building_id,
        notification_timeline=timeline,
        key_messages=key_messages,
        affected_parties=affected_parties,
        language_requirements=languages,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_occupancy_risk
# ---------------------------------------------------------------------------


async def get_portfolio_occupancy_risk(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioOccupancyRisk:
    """
    Portfolio-level occupancy risk overview for an organization.
    Returns distribution of buildings by risk level, total affected occupants,
    relocation needs, and high-priority buildings list.
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
        return PortfolioOccupancyRisk(
            organization_id=org_id,
            buildings_by_risk_level={"low": 0, "medium": 0, "high": 0, "critical": 0},
            total_affected_occupants=0,
            relocation_needs_count=0,
            high_priority_buildings=[],
            evaluated_at=datetime.now(UTC),
        )

    distribution: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    total_affected = 0
    relocation_count = 0
    high_priority: list[HighPriorityBuilding] = []

    for bldg in buildings:
        try:
            assessment = await assess_occupancy_risk(bldg.id, db)
        except ValueError:
            continue

        level = assessment.risk_level
        distribution[level.value] = distribution.get(level.value, 0) + 1

        if level in (OccupancyRiskLevel.high, OccupancyRiskLevel.critical):
            total_affected += assessment.occupant_count_estimate

            # Check relocation
            try:
                reloc = await evaluate_temporary_relocation(bldg.id, db)
                if reloc.relocation_needed:
                    relocation_count += 1
            except ValueError:
                pass

            high_priority.append(
                HighPriorityBuilding(
                    building_id=bldg.id,
                    address=bldg.address,
                    city=bldg.city,
                    risk_level=level,
                    occupant_count_estimate=assessment.occupant_count_estimate,
                    relocation_needed=reloc.relocation_needed if reloc else False,
                )
            )

    # Sort high priority: critical first
    high_priority.sort(key=lambda b: _RISK_ORDER.get(b.risk_level, 0), reverse=True)

    return PortfolioOccupancyRisk(
        organization_id=org_id,
        buildings_by_risk_level=distribution,
        total_affected_occupants=total_affected,
        relocation_needs_count=relocation_count,
        high_priority_buildings=high_priority,
        evaluated_at=datetime.now(UTC),
    )
