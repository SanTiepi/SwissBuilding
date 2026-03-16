"""
SwissBuildingOS - Access Control Service

Generates per-zone access restrictions, safe zone lists, permit requirements,
and portfolio-level access compliance based on pollutant status.

Swiss regulatory basis:
- OTConst Art. 60a, 82-86: asbestos work restrictions
- CFST 6503: work categories (minor/medium/major) -> PPE and cert levels
- SUVA certification for asbestos handling
- ORRChim Annexe 2.15 (PCB), 2.18 (lead): threshold-based restrictions
- ORaP Art. 110 (radon): 300/1000 Bq/m3 thresholds
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
from app.schemas.access_control import (
    AccessLevel,
    BuildingAccessRestrictions,
    BuildingAccessSummary,
    BuildingPermitRequirements,
    BuildingSafeZones,
    MaskType,
    PortfolioAccessStatus,
    PPERequirement,
    SafeZone,
    SignageRequirement,
    SuitType,
    SUVACertLevel,
    ZoneAccessRestriction,
    ZonePermitRequirement,
)

# Friable material states that indicate airborne risk
_FRIABLE_STATES = {"friable", "friable_damaged", "degraded", "damaged"}

# Zone types considered habitable
_HABITABLE_ZONE_TYPES = {"floor", "room", "staircase"}


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


def _collect_zone_pollutants(
    zones: list[Zone],
    samples: list[Sample],
) -> dict[UUID, list[dict]]:
    """
    Collect pollutant data per zone from materials and samples.
    Returns {zone_id: [pollutant_info_dict, ...]}.
    """
    zone_pollutants: dict[UUID, list[dict]] = {}

    for zone in zones:
        zone_pollutants.setdefault(zone.id, [])
        for element in zone.elements:
            for material in element.materials:
                if material.contains_pollutant and material.pollutant_type:
                    zone_pollutants[zone.id].append(
                        {
                            "pollutant_type": material.pollutant_type,
                            "material_state": material.source,
                            "concentration": None,
                            "unit": None,
                            "cfst_work_category": None,
                        }
                    )

    for sample in samples:
        if not sample.pollutant_type:
            continue
        matched = False
        for zone in zones:
            if sample.location_floor and zone.name and sample.location_floor.lower() in zone.name.lower():
                zone_pollutants.setdefault(zone.id, []).append(
                    {
                        "pollutant_type": sample.pollutant_type,
                        "material_state": sample.material_state,
                        "concentration": sample.concentration,
                        "unit": sample.unit,
                        "cfst_work_category": sample.cfst_work_category,
                    }
                )
                matched = True
                break
        if not matched and zones:
            zone_pollutants.setdefault(zones[0].id, []).append(
                {
                    "pollutant_type": sample.pollutant_type,
                    "material_state": sample.material_state,
                    "concentration": sample.concentration,
                    "unit": sample.unit,
                    "cfst_work_category": sample.cfst_work_category,
                }
            )

    return zone_pollutants


def _determine_access_level(pollutants: list[dict], zone_type: str) -> tuple[AccessLevel, str]:
    """
    Determine access level for a zone based on its pollutants.
    Returns (access_level, reason).
    """
    if not pollutants:
        return AccessLevel.unrestricted, "Aucun polluant detecte"

    worst = AccessLevel.unrestricted
    reason = "Aucun polluant detecte"

    for p in pollutants:
        pt = (p["pollutant_type"] or "").lower()
        state = (p["material_state"] or "").lower()
        concentration = p.get("concentration")
        habitable = zone_type in _HABITABLE_ZONE_TYPES

        level = AccessLevel.unrestricted
        r = ""

        if pt == "asbestos":
            if state in _FRIABLE_STATES and habitable:
                level = AccessLevel.prohibited
                r = "Amiante friable en zone habitable - acces interdit"
            elif state in _FRIABLE_STATES:
                level = AccessLevel.restricted_authorized
                r = "Amiante friable - personnel autorise SUVA uniquement"
            elif habitable:
                level = AccessLevel.restricted_ppe
                r = "Amiante non-friable en zone habitable - EPI requis pour intervention"
            else:
                level = AccessLevel.unrestricted
                r = "Amiante encapsule en zone technique - acces libre sous surveillance"

        elif pt == "radon":
            if concentration is not None and concentration > 1000:
                level = AccessLevel.prohibited
                r = f"Radon {concentration} Bq/m3 - acces interdit"
            elif concentration is not None and concentration > 300:
                level = AccessLevel.restricted_ppe
                r = f"Radon {concentration} Bq/m3 - ventilation et duree limitee"

        elif pt == "pcb":
            if concentration is not None and concentration > 50:
                if habitable:
                    level = AccessLevel.restricted_authorized
                    r = f"PCB {concentration} mg/kg en zone habitable - acces restreint"
                else:
                    level = AccessLevel.restricted_ppe
                    r = f"PCB {concentration} mg/kg - EPI requis"

        elif pt == "lead":
            if concentration is not None and concentration > 5000:
                if habitable:
                    level = AccessLevel.restricted_authorized
                    r = "Plomb au-dessus du seuil en zone habitable - acces autorise uniquement"
                else:
                    level = AccessLevel.restricted_ppe
                    r = "Plomb au-dessus du seuil - EPI requis"

        elif pt == "hap" and habitable:
            level = AccessLevel.restricted_ppe
            r = "HAP en zone habitable - EPI requis pour intervention"

        # Keep worst
        _order = {
            AccessLevel.unrestricted: 0,
            AccessLevel.restricted_ppe: 1,
            AccessLevel.restricted_authorized: 2,
            AccessLevel.prohibited: 3,
        }
        if _order[level] > _order[worst]:
            worst = level
            reason = r

    return worst, reason


_ACCESS_LEVEL_ORDER = {
    AccessLevel.unrestricted: 0,
    AccessLevel.restricted_ppe: 1,
    AccessLevel.restricted_authorized: 2,
    AccessLevel.prohibited: 3,
}


def _get_ppe_for_zone(pollutants: list[dict], access_level: AccessLevel) -> PPERequirement | None:
    """Determine PPE requirements based on pollutants and access level."""
    if access_level == AccessLevel.unrestricted:
        return None

    pollutant_types = {(p["pollutant_type"] or "").lower() for p in pollutants if p["pollutant_type"]}
    states = {(p["material_state"] or "").lower() for p in pollutants}

    mask: MaskType | None = None
    suit: SuitType | None = None
    gloves = False
    goggles = False
    desc_parts: list[str] = []

    if "asbestos" in pollutant_types:
        if states & _FRIABLE_STATES:
            mask = MaskType.full_face_p3
            suit = SuitType.type_3_4
            gloves = True
            goggles = True
            desc_parts.append("Protection complete amiante friable")
        else:
            mask = MaskType.ffp3
            suit = SuitType.disposable
            gloves = True
            desc_parts.append("Protection amiante non-friable")

    if "radon" in pollutant_types:
        if mask is None or mask == MaskType.ffp2:
            mask = MaskType.ffp2
        desc_parts.append("Protection radon - ventilation requise")

    if "pcb" in pollutant_types:
        gloves = True
        goggles = True
        if mask is None:
            mask = MaskType.ffp2
        if suit is None:
            suit = SuitType.disposable
        desc_parts.append("Protection PCB - eviter contact cutane")

    if "lead" in pollutant_types:
        gloves = True
        if mask is None:
            mask = MaskType.ffp2
        if suit is None:
            suit = SuitType.disposable
        desc_parts.append("Protection plomb")

    if "hap" in pollutant_types:
        gloves = True
        if mask is None:
            mask = MaskType.ffp2
        desc_parts.append("Protection HAP")

    return PPERequirement(
        mask_type=mask,
        suit_type=suit,
        gloves_required=gloves,
        safety_goggles=goggles,
        description="; ".join(desc_parts) if desc_parts else "EPI requis",
    )


def _get_signage_for_zone(pollutants: list[dict], access_level: AccessLevel) -> list[SignageRequirement]:
    """Determine signage requirements for a zone."""
    if access_level == AccessLevel.unrestricted:
        return []

    signage: list[SignageRequirement] = []
    pollutant_types = {(p["pollutant_type"] or "").lower() for p in pollutants if p["pollutant_type"]}

    if access_level == AccessLevel.prohibited:
        signage.append(
            SignageRequirement(
                sign_type="danger",
                text_fr="ACCES INTERDIT - Zone contaminee",
                mandatory=True,
            )
        )

    if access_level in (AccessLevel.restricted_ppe, AccessLevel.restricted_authorized):
        signage.append(
            SignageRequirement(
                sign_type="warning",
                text_fr="ACCES RESTREINT - Equipement de protection obligatoire",
                mandatory=True,
            )
        )

    if "asbestos" in pollutant_types:
        signage.append(
            SignageRequirement(
                sign_type="pollutant",
                text_fr="ATTENTION AMIANTE - Ne pas percer, poncer ou casser",
                mandatory=True,
            )
        )

    if "radon" in pollutant_types:
        signage.append(
            SignageRequirement(
                sign_type="pollutant",
                text_fr="RADON - Ventiler avant et pendant le sejour",
                mandatory=True,
            )
        )

    if "pcb" in pollutant_types:
        signage.append(
            SignageRequirement(
                sign_type="pollutant",
                text_fr="PCB - Eviter tout contact direct",
                mandatory=True,
            )
        )

    if "lead" in pollutant_types:
        signage.append(
            SignageRequirement(
                sign_type="pollutant",
                text_fr="PLOMB - Ne pas gratter les peintures",
                mandatory=True,
            )
        )

    return signage


async def generate_access_restrictions(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingAccessRestrictions:
    """
    Generate per-zone access rules based on pollutant status.
    Determines access level, PPE, and signage for each zone.
    """
    await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_pollutants = _collect_zone_pollutants(zones, samples)

    zone_restrictions: list[ZoneAccessRestriction] = []
    restricted = 0
    prohibited = 0

    for zone in zones:
        pollutants = zone_pollutants.get(zone.id, [])
        access_level, reason = _determine_access_level(pollutants, zone.zone_type)

        ppe = _get_ppe_for_zone(pollutants, access_level)
        signage = _get_signage_for_zone(pollutants, access_level)

        pollutant_types = list({p["pollutant_type"] for p in pollutants if p["pollutant_type"]})

        if access_level in (AccessLevel.restricted_ppe, AccessLevel.restricted_authorized):
            restricted += 1
        elif access_level == AccessLevel.prohibited:
            prohibited += 1

        zone_restrictions.append(
            ZoneAccessRestriction(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                floor_number=zone.floor_number,
                access_level=access_level,
                reason=reason,
                pollutant_types=pollutant_types,
                ppe=ppe,
                signage=signage,
            )
        )

    return BuildingAccessRestrictions(
        building_id=building_id,
        zones=zone_restrictions,
        total_zones=len(zones),
        restricted_zones=restricted,
        prohibited_zones=prohibited,
        evaluated_at=datetime.now(UTC),
    )


async def get_safe_zones(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingSafeZones:
    """
    Return zones confirmed safe for unrestricted access:
    no pollutants detected, cleared, or encapsulated with valid monitoring.
    """
    await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_pollutants = _collect_zone_pollutants(zones, samples)

    safe_zones: list[SafeZone] = []
    restricted_count = 0

    for zone in zones:
        pollutants = zone_pollutants.get(zone.id, [])
        access_level, _ = _determine_access_level(pollutants, zone.zone_type)

        if access_level == AccessLevel.unrestricted:
            if not pollutants:
                reason = "Aucun polluant detecte - acces libre"
            else:
                reason = "Polluants encapsules ou sous seuil - acces libre sous surveillance"
            safe_zones.append(
                SafeZone(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    zone_type=zone.zone_type,
                    floor_number=zone.floor_number,
                    reason=reason,
                )
            )
        else:
            restricted_count += 1

    total = len(zones)
    safe_ratio = len(safe_zones) / total if total > 0 else 1.0

    return BuildingSafeZones(
        building_id=building_id,
        safe_zones=safe_zones,
        restricted_zones_count=restricted_count,
        total_zones=total,
        safe_ratio=safe_ratio,
        evaluated_at=datetime.now(UTC),
    )


def _get_suva_cert_level(pollutants: list[dict], access_level: AccessLevel) -> SUVACertLevel:
    """Determine SUVA certification level based on pollutants and access."""
    if access_level == AccessLevel.unrestricted:
        return SUVACertLevel.none

    pollutant_types = {(p["pollutant_type"] or "").lower() for p in pollutants if p["pollutant_type"]}
    states = {(p["material_state"] or "").lower() for p in pollutants}
    cfst_cats = {p.get("cfst_work_category") for p in pollutants if p.get("cfst_work_category")}

    if "asbestos" in pollutant_types:
        if states & _FRIABLE_STATES or "major" in cfst_cats:
            return SUVACertLevel.specialist
        if "medium" in cfst_cats:
            return SUVACertLevel.advanced
        return SUVACertLevel.basic

    if access_level == AccessLevel.restricted_authorized:
        return SUVACertLevel.advanced

    if access_level == AccessLevel.restricted_ppe:
        return SUVACertLevel.basic

    return SUVACertLevel.none


def _get_training_requirements(pollutants: list[dict], access_level: AccessLevel) -> list[str]:
    """Determine training requirements for zone access."""
    if access_level == AccessLevel.unrestricted:
        return []

    reqs: list[str] = []
    pollutant_types = {(p["pollutant_type"] or "").lower() for p in pollutants if p["pollutant_type"]}
    states = {(p["material_state"] or "").lower() for p in pollutants}

    if "asbestos" in pollutant_types:
        if states & _FRIABLE_STATES:
            reqs.append("Formation SUVA amiante friable (2 jours)")
            reqs.append("Procedure de decontamination")
        else:
            reqs.append("Sensibilisation amiante (4 heures)")

    if "pcb" in pollutant_types:
        reqs.append("Formation manipulation PCB")

    if "lead" in pollutant_types:
        reqs.append("Formation risques plomb")

    if "radon" in pollutant_types:
        reqs.append("Sensibilisation radon et mesures de ventilation")

    if access_level in (AccessLevel.restricted_ppe, AccessLevel.restricted_authorized):
        reqs.append("Formation port EPI")

    return reqs


async def generate_access_permit_requirements(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingPermitRequirements:
    """
    Determine permits/authorizations needed to enter restricted zones:
    SUVA certification level, medical clearance, training, escort.
    """
    await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_pollutants = _collect_zone_pollutants(zones, samples)

    zone_permits: list[ZonePermitRequirement] = []
    max_cert = SUVACertLevel.none
    any_medical = False
    zones_requiring = 0

    cert_order = {
        SUVACertLevel.none: 0,
        SUVACertLevel.basic: 1,
        SUVACertLevel.advanced: 2,
        SUVACertLevel.specialist: 3,
    }

    for zone in zones:
        pollutants = zone_pollutants.get(zone.id, [])
        access_level, _ = _determine_access_level(pollutants, zone.zone_type)

        if access_level == AccessLevel.unrestricted:
            continue

        zones_requiring += 1

        suva_cert = _get_suva_cert_level(pollutants, access_level)
        training = _get_training_requirements(pollutants, access_level)

        # Medical clearance for specialist work or prohibited zones
        medical = access_level == AccessLevel.prohibited or suva_cert == SUVACertLevel.specialist

        # Escort for authorized-only zones
        escort = access_level in (AccessLevel.restricted_authorized, AccessLevel.prohibited)
        escort_desc = None
        if escort:
            escort_desc = "Accompagnement par responsable securite obligatoire"

        pollutant_types = list({p["pollutant_type"] for p in pollutants if p["pollutant_type"]})

        if cert_order[suva_cert] > cert_order[max_cert]:
            max_cert = suva_cert
        if medical:
            any_medical = True

        zone_permits.append(
            ZonePermitRequirement(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                access_level=access_level,
                suva_cert_level=suva_cert,
                medical_clearance_required=medical,
                training_requirements=training,
                escort_required=escort,
                escort_description=escort_desc,
                pollutant_types=pollutant_types,
            )
        )

    return BuildingPermitRequirements(
        building_id=building_id,
        zones=zone_permits,
        zones_requiring_permits=zones_requiring,
        max_suva_cert_level=max_cert,
        any_medical_clearance=any_medical,
        evaluated_at=datetime.now(UTC),
    )


async def get_portfolio_access_status(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioAccessStatus:
    """
    Org-level access status: buildings with restrictions, total restricted zones,
    buildings fully accessible, access compliance rate.
    """
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioAccessStatus(
            organization_id=org_id,
            total_buildings=0,
            buildings_with_restrictions=0,
            buildings_fully_accessible=0,
            total_restricted_zones=0,
            access_compliance_rate=1.0,
            buildings=[],
            evaluated_at=datetime.now(UTC),
        )

    summaries: list[BuildingAccessSummary] = []
    with_restrictions = 0
    fully_accessible = 0
    total_restricted = 0

    for bldg in buildings:
        try:
            restrictions = await generate_access_restrictions(db, bldg.id)
        except ValueError:
            continue

        restricted = restrictions.restricted_zones + restrictions.prohibited_zones
        total_restricted += restricted
        is_fully = restricted == 0

        if is_fully:
            fully_accessible += 1
        else:
            with_restrictions += 1

        summaries.append(
            BuildingAccessSummary(
                building_id=bldg.id,
                address=bldg.address,
                city=bldg.city,
                total_zones=restrictions.total_zones,
                restricted_zones=restrictions.restricted_zones,
                prohibited_zones=restrictions.prohibited_zones,
                fully_accessible=is_fully,
            )
        )

    total = len(buildings)
    compliance_rate = fully_accessible / total if total > 0 else 1.0

    # Sort: buildings with restrictions first
    summaries.sort(key=lambda b: b.fully_accessible)

    return PortfolioAccessStatus(
        organization_id=org_id,
        total_buildings=total,
        buildings_with_restrictions=with_restrictions,
        buildings_fully_accessible=fully_accessible,
        total_restricted_zones=total_restricted,
        access_compliance_rate=compliance_rate,
        buildings=summaries,
        evaluated_at=datetime.now(UTC),
    )
