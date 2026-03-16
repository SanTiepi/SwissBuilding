"""
SwissBuildingOS - Incident Response Service

Generates emergency response plans for pollutant incidents in buildings:
- Fiber release (asbestos)
- Spill (PCB / lead paint)
- Elevated radon reading

Swiss regulatory references:
- OTConst Art. 60a, 82-86 (asbestos incidents)
- CFST 6503 (work categories / emergency measures)
- ORRChim Annexe 2.15 (PCB spill), 2.18 (lead)
- ORaP Art. 110 (radon: 300/1000 Bq/m3)
- SUVA notification requirements
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.user import User
from app.models.zone import Zone
from app.schemas.incident_response import (
    BuildingIncidentProbability,
    BuildingIncidentSummary,
    ContactRole,
    EmergencyContact,
    EmergencyContactList,
    IncidentAction,
    IncidentPlan,
    IncidentScenario,
    PortfolioIncidentReadiness,
    RiskLevel,
    ScenarioResponse,
    ZoneIncidentRisk,
)

# Zone types considered public / high-traffic
_PUBLIC_ZONE_TYPES = {"floor", "room", "staircase"}

# Material states that indicate degradation
_DEGRADED_STATES = {"degraded", "damaged", "friable", "friable_damaged"}

# Active intervention statuses
_ACTIVE_INTERVENTION_STATUSES = {"planned", "in_progress"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _load_zones_with_materials(db: AsyncSession, building_id: UUID) -> list[Zone]:
    result = await db.execute(
        select(Zone)
        .where(Zone.building_id == building_id)
        .options(selectinload(Zone.elements).selectinload(BuildingElement.materials))
    )
    return list(result.scalars().all())


async def _load_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    return list(result.scalars().all())


def _collect_zone_pollutants(zones: list[Zone]) -> dict[UUID, list[str]]:
    """Collect unique pollutant types per zone from materials."""
    zone_pollutants: dict[UUID, list[str]] = {}
    for zone in zones:
        pollutants: list[str] = []
        for element in zone.elements:
            for material in element.materials:
                if (
                    material.contains_pollutant
                    and material.pollutant_type
                    and material.pollutant_type not in pollutants
                ):
                    pollutants.append(material.pollutant_type)
        zone_pollutants[zone.id] = pollutants
    return zone_pollutants


def _has_degraded_materials(zone: Zone) -> bool:
    """Check if any element in the zone has degraded condition or materials with degraded source."""
    for element in zone.elements:
        if element.condition and element.condition.lower() in _DEGRADED_STATES:
            return True
        for material in element.materials:
            if material.source and material.source.lower() in _DEGRADED_STATES:
                return True
    return False


def _zone_has_active_intervention(zone: Zone, interventions: list[Intervention]) -> bool:
    """Check if any active intervention affects the zone."""
    for iv in interventions:
        if iv.status not in _ACTIVE_INTERVENTION_STATUSES:
            continue
        # Check zones_affected JSON field
        if iv.zones_affected:
            zone_id_str = str(zone.id)
            if isinstance(iv.zones_affected, list):
                if zone_id_str in [str(z) for z in iv.zones_affected]:
                    return True
            elif isinstance(iv.zones_affected, dict) and zone_id_str in iv.zones_affected:
                return True
        # If no zones_affected specified, any active intervention on the building counts
        if not iv.zones_affected:
            return True
    return False


# ---------------------------------------------------------------------------
# FN1: generate_incident_plan
# ---------------------------------------------------------------------------

_FIBER_RELEASE_ACTIONS = [
    IncidentAction(
        step=1,
        description="Evacuer immediatement la zone concernee",
        responsible="Responsable batiment",
        timeframe="Immediat",
    ),
    IncidentAction(
        step=2,
        description="Fermer et sceller les acces a la zone contaminee",
        responsible="Responsable batiment",
        timeframe="< 15 min",
    ),
    IncidentAction(
        step=3,
        description="Couper la ventilation et climatisation de la zone",
        responsible="Service technique",
        timeframe="< 15 min",
    ),
    IncidentAction(
        step=4,
        description="Contacter une entreprise de desamiantage reconnue SUVA",
        responsible="Gestionnaire",
        timeframe="< 1 heure",
    ),
    IncidentAction(
        step=5,
        description="Notifier la SUVA et l'autorite cantonale",
        responsible="Gestionnaire",
        timeframe="< 24 heures",
    ),
]

_SPILL_ACTIONS = [
    IncidentAction(
        step=1,
        description="Isoler la zone du deversement - empecher la propagation",
        responsible="Responsable batiment",
        timeframe="Immediat",
    ),
    IncidentAction(
        step=2,
        description="Ventiler la zone si securitaire",
        responsible="Service technique",
        timeframe="< 15 min",
    ),
    IncidentAction(
        step=3,
        description="Eviter tout contact direct - porter EPI si intervention necessaire",
        responsible="Personnel present",
        timeframe="Immediat",
    ),
    IncidentAction(
        step=4,
        description="Contacter une entreprise specialisee pour decontamination",
        responsible="Gestionnaire",
        timeframe="< 1 heure",
    ),
    IncidentAction(
        step=5,
        description="Notifier l'autorite cantonale et le service de l'environnement",
        responsible="Gestionnaire",
        timeframe="< 24 heures",
    ),
]

_RADON_ACTIONS = [
    IncidentAction(
        step=1,
        description="Ouvrir les fenetres et maximiser la ventilation naturelle",
        responsible="Responsable batiment",
        timeframe="Immediat",
    ),
    IncidentAction(
        step=2,
        description="Limiter le temps de sejour dans les zones concernees",
        responsible="Responsable batiment",
        timeframe="Immediat",
    ),
    IncidentAction(
        step=3,
        description="Effectuer des mesures de confirmation avec dosimetre",
        responsible="Diagnostiqueur",
        timeframe="< 48 heures",
    ),
    IncidentAction(
        step=4,
        description="Contacter le service cantonal de radioprotection (OFSP)",
        responsible="Gestionnaire",
        timeframe="< 1 semaine",
    ),
    IncidentAction(
        step=5,
        description="Planifier l'installation d'un systeme d'assainissement radon",
        responsible="Specialiste radon",
        timeframe="< 1 mois",
    ),
]


def _build_scenario_response(
    scenario: IncidentScenario,
    zone_names: list[str],
    canton: str,
) -> ScenarioResponse:
    """Build a scenario response based on the incident type."""
    if scenario == IncidentScenario.fiber_release:
        return ScenarioResponse(
            scenario=scenario,
            pollutant="asbestos",
            immediate_actions=_FIBER_RELEASE_ACTIONS,
            evacuation_zones=zone_names if zone_names else ["Toutes les zones adjacentes"],
            decontamination_steps=[
                "Aspirateur HEPA sur toutes les surfaces",
                "Nettoyage humide des surfaces non poreuses",
                "Mesures d'air apres decontamination (< 0.01 f/ml)",
                "Elimination des dechets en tant que dechets speciaux (OLED)",
            ],
            notification_chain=[
                "Responsable batiment",
                "Gestionnaire / proprietaire",
                "SUVA (si travailleurs exposes)",
                f"Autorite cantonale {canton}",
                "Occupants concernes",
            ],
            authority_reporting=[
                "Annonce SUVA dans les 24h si exposition de travailleurs",
                f"Notification service sante canton {canton}",
                "Documentation photographique de l'incident",
                "Rapport de decontamination par entreprise reconnue",
            ],
        )

    if scenario == IncidentScenario.spill:
        return ScenarioResponse(
            scenario=scenario,
            pollutant="pcb_lead",
            immediate_actions=_SPILL_ACTIONS,
            evacuation_zones=zone_names if zone_names else ["Zone du deversement + zones adjacentes"],
            decontamination_steps=[
                "Absorption du produit avec materiau absorbant inerte",
                "Nettoyage specialise selon type de polluant (PCB / plomb)",
                "Verification des seuils reglementaires apres nettoyage",
                "Elimination en tant que dechets speciaux (OLED type_e)",
            ],
            notification_chain=[
                "Responsable batiment",
                "Gestionnaire / proprietaire",
                f"Service environnement canton {canton}",
                "Pompiers (si quantite importante)",
            ],
            authority_reporting=[
                f"Notification service environnement canton {canton}",
                "Rapport de decontamination",
                "Analyses de sol / surfaces apres nettoyage",
            ],
        )

    # elevated_radon
    return ScenarioResponse(
        scenario=scenario,
        pollutant="radon",
        immediate_actions=_RADON_ACTIONS,
        evacuation_zones=zone_names if zone_names else ["Sous-sol", "Rez-de-chaussee"],
        decontamination_steps=[
            "Pas de decontamination physique necessaire",
            "Amelioration de l'etancheite sol/murs du sous-sol",
            "Installation de ventilation mecanique ou puits radon",
            "Mesures de controle apres travaux (dosimetrie 3 mois)",
        ],
        notification_chain=[
            "Responsable batiment",
            "Gestionnaire / proprietaire",
            "OFSP / service cantonal radioprotection",
            "Occupants concernes",
        ],
        authority_reporting=[
            "Mesures radon > 300 Bq/m3: notification au canton recommandee",
            "Mesures radon > 1000 Bq/m3: notification obligatoire (ORaP Art. 110)",
            "Rapport de mesures par laboratoire reconnu",
        ],
    )


async def generate_incident_plan(
    db: AsyncSession,
    building_id: UUID,
) -> IncidentPlan:
    """Generate emergency response plan for pollutant incidents in a building."""
    building = await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    zone_pollutants = _collect_zone_pollutants(zones)

    # Determine which scenarios are relevant based on detected pollutants
    all_pollutants: set[str] = set()
    for plist in zone_pollutants.values():
        all_pollutants.update(p.lower() for p in plist)

    scenarios: list[ScenarioResponse] = []

    # Always include fiber_release if asbestos present, else include as template
    if "asbestos" in all_pollutants:
        asbestos_zones = [z.name for z in zones if any(p.lower() == "asbestos" for p in zone_pollutants.get(z.id, []))]
        scenarios.append(
            _build_scenario_response(IncidentScenario.fiber_release, asbestos_zones, building.canton or "VD")
        )
    else:
        scenarios.append(_build_scenario_response(IncidentScenario.fiber_release, [], building.canton or "VD"))

    # Spill scenario for PCB / lead
    if "pcb" in all_pollutants or "lead" in all_pollutants:
        spill_zones = [
            z.name for z in zones if any(p.lower() in ("pcb", "lead") for p in zone_pollutants.get(z.id, []))
        ]
        scenarios.append(_build_scenario_response(IncidentScenario.spill, spill_zones, building.canton or "VD"))
    else:
        scenarios.append(_build_scenario_response(IncidentScenario.spill, [], building.canton or "VD"))

    # Radon
    if "radon" in all_pollutants:
        radon_zones = [z.name for z in zones if any(p.lower() == "radon" for p in zone_pollutants.get(z.id, []))]
        scenarios.append(
            _build_scenario_response(IncidentScenario.elevated_radon, radon_zones, building.canton or "VD")
        )
    else:
        scenarios.append(_build_scenario_response(IncidentScenario.elevated_radon, [], building.canton or "VD"))

    return IncidentPlan(
        building_id=building_id,
        address=building.address or "",
        canton=building.canton or "VD",
        scenarios=scenarios,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: get_emergency_contacts
# ---------------------------------------------------------------------------


async def get_emergency_contacts(
    db: AsyncSession,
    building_id: UUID,
) -> EmergencyContactList:
    """Get structured emergency contact list based on assignments + org type."""
    building = await _load_building(db, building_id)

    contacts: list[EmergencyContact] = []

    # Get assignments for this building
    result = await db.execute(
        select(Assignment)
        .where(Assignment.target_type == "building", Assignment.target_id == building_id)
        .options(selectinload(Assignment.user))
    )
    assignments = list(result.scalars().all())

    # Map assignment roles to contact roles
    role_mapping: dict[str, ContactRole] = {
        "owner_contact": ContactRole.building_owner,
        "responsible": ContactRole.building_owner,
        "diagnostician": ContactRole.diagnostician,
        "contractor_contact": ContactRole.contractor,
        "reviewer": ContactRole.diagnostician,
    }

    for assignment in assignments:
        user = assignment.user
        if not user:
            continue

        contact_role = role_mapping.get(assignment.role)
        if not contact_role:
            continue

        # Load user's organization
        org_name = None
        if user.organization_id:
            org_result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
            org = org_result.scalar_one_or_none()
            if org:
                org_name = org.name

        contacts.append(
            EmergencyContact(
                role=contact_role,
                name=f"{user.first_name} {user.last_name}",
                organization=org_name,
                phone=None,
                email=user.email,
            )
        )

    # Add building creator as fallback owner if no owner_contact assigned
    if not any(c.role == ContactRole.building_owner for c in contacts):
        creator_result = await db.execute(select(User).where(User.id == building.created_by))
        creator = creator_result.scalar_one_or_none()
        if creator:
            contacts.append(
                EmergencyContact(
                    role=ContactRole.building_owner,
                    name=f"{creator.first_name} {creator.last_name}",
                    email=creator.email,
                )
            )

    # Add statutory contacts
    canton = building.canton or "VD"
    contacts.append(
        EmergencyContact(
            role=ContactRole.suva,
            name="SUVA - Caisse nationale suisse d'assurance",
            organization="SUVA",
            phone="041 419 51 11",
            email="serviceclientele@suva.ch",
        )
    )
    contacts.append(
        EmergencyContact(
            role=ContactRole.cantonal_authority,
            name=f"Autorite cantonale {canton}",
            organization=f"Service de la sante publique - Canton {canton}",
        )
    )
    contacts.append(
        EmergencyContact(
            role=ContactRole.emergency_services,
            name="Services d'urgence",
            organization="Pompiers / Police / Ambulance",
            phone="118 / 117 / 144",
        )
    )

    return EmergencyContactList(
        building_id=building_id,
        contacts=contacts,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: assess_incident_probability
# ---------------------------------------------------------------------------


def _assess_zone_risk(
    zone: Zone,
    zone_pollutants: list[str],
    has_degraded: bool,
    has_active_intervention: bool,
) -> ZoneIncidentRisk:
    """Assess incident probability for a single zone."""
    factors: list[str] = []
    score = 0.0

    is_public = zone.zone_type in _PUBLIC_ZONE_TYPES

    # Factor 1: Material condition
    if has_degraded:
        score += 0.35
        factors.append("Materiaux en etat degrade")

    # Factor 2: Accessibility / public zone
    if is_public:
        score += 0.20
        factors.append("Zone accessible au public")

    # Factor 3: Active intervention
    if has_active_intervention:
        score += 0.30
        factors.append("Intervention active en cours")

    # Factor 4: Pollutants present
    if zone_pollutants:
        score += 0.15
        factors.append(f"Polluants presents: {', '.join(zone_pollutants)}")

    # Clamp
    score = min(score, 1.0)

    # Determine risk level
    if score >= 0.7:
        risk_level = RiskLevel.critical
    elif score >= 0.5:
        risk_level = RiskLevel.high
    elif score >= 0.25:
        risk_level = RiskLevel.medium
    else:
        risk_level = RiskLevel.low

    return ZoneIncidentRisk(
        zone_id=zone.id,
        zone_name=zone.name,
        zone_type=zone.zone_type,
        risk_level=risk_level,
        probability_score=round(score, 2),
        factors=factors,
        pollutants_present=zone_pollutants,
        has_degraded_material=has_degraded,
        is_public_zone=is_public,
        has_active_intervention=has_active_intervention,
    )


_RISK_ORDER = {
    RiskLevel.low: 0,
    RiskLevel.medium: 1,
    RiskLevel.high: 2,
    RiskLevel.critical: 3,
}


async def assess_incident_probability(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingIncidentProbability:
    """Assess incident probability per zone for a building."""
    await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    interventions = await _load_interventions(db, building_id)
    zone_pollutants = _collect_zone_pollutants(zones)

    zone_risks: list[ZoneIncidentRisk] = []

    for zone in zones:
        pollutants = zone_pollutants.get(zone.id, [])
        has_degraded = _has_degraded_materials(zone)
        has_active = _zone_has_active_intervention(zone, interventions)

        risk = _assess_zone_risk(zone, pollutants, has_degraded, has_active)
        zone_risks.append(risk)

    # Sort by risk level descending
    zone_risks.sort(key=lambda z: _RISK_ORDER[z.risk_level], reverse=True)

    high_risk_zones = sum(1 for z in zone_risks if z.risk_level in (RiskLevel.high, RiskLevel.critical))
    overall_level = RiskLevel.low
    if zone_risks:
        overall_level = zone_risks[0].risk_level  # worst zone

    return BuildingIncidentProbability(
        building_id=building_id,
        zones=zone_risks,
        overall_risk_level=overall_level,
        highest_risk_zone=zone_risks[0].zone_name if zone_risks else None,
        total_zones=len(zones),
        high_risk_zones=high_risk_zones,
        assessed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_incident_readiness
# ---------------------------------------------------------------------------


async def get_portfolio_incident_readiness(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioIncidentReadiness:
    """Organization-level incident readiness: buildings with plans, high risk, coverage gaps."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioIncidentReadiness(
            organization_id=org_id,
            total_buildings=0,
            buildings_with_plans=0,
            buildings_high_risk=0,
            coverage_gaps=[],
            buildings_needing_plans=0,
            buildings=[],
            assessed_at=datetime.now(UTC),
        )

    summaries: list[BuildingIncidentSummary] = []
    high_risk_count = 0
    buildings_with_pollutants = 0
    coverage_gaps: list[str] = []

    for bldg in buildings:
        try:
            probability = await assess_incident_probability(db, bldg.id)
        except ValueError:
            continue

        has_pollutants = any(z.pollutants_present for z in probability.zones)
        if has_pollutants:
            buildings_with_pollutants += 1

        is_high_risk = probability.overall_risk_level in (RiskLevel.high, RiskLevel.critical)
        if is_high_risk:
            high_risk_count += 1

        summaries.append(
            BuildingIncidentSummary(
                building_id=bldg.id,
                address=bldg.address or "",
                city=bldg.city or "",
                has_incident_plan=has_pollutants,  # plan exists if pollutants assessed
                risk_level=probability.overall_risk_level,
                high_risk_zones=probability.high_risk_zones,
            )
        )

    # Coverage gaps
    buildings_without_data = len(buildings) - buildings_with_pollutants
    if buildings_without_data > 0:
        coverage_gaps.append(f"{buildings_without_data} batiment(s) sans diagnostic polluant")
    if high_risk_count > 0:
        coverage_gaps.append(f"{high_risk_count} batiment(s) a risque eleve necessitant un plan d'urgence")

    return PortfolioIncidentReadiness(
        organization_id=org_id,
        total_buildings=len(buildings),
        buildings_with_plans=buildings_with_pollutants,
        buildings_high_risk=high_risk_count,
        coverage_gaps=coverage_gaps,
        buildings_needing_plans=max(0, high_risk_count - buildings_with_pollutants) + buildings_without_data,
        buildings=summaries,
        assessed_at=datetime.now(UTC),
    )
