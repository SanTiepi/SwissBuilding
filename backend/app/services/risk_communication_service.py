"""
SwissBuildingOS - Risk Communication Service

Generates human-readable risk communications for different audiences:
- Occupant notices (plain-language, reassuring)
- Worker safety briefings (CFST 6503-aligned)
- Stakeholder notifications (audience-specific detail level)
- Communication audit log
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.risk_communication import (
    CommunicationLog,
    CommunicationLogEntry,
    DecontaminationStep,
    OccupantNotice,
    OccupantNoticeSection,
    PPERequirement,
    StakeholderAction,
    StakeholderNotification,
    WorkerSafetyBriefing,
    ZoneBriefing,
)

# ---------------------------------------------------------------------------
# Internal: in-memory communication log (per-process, for audit trail)
# ---------------------------------------------------------------------------

_communication_log: dict[str, list[dict]] = {}

POLLUTANT_LABELS = {
    "asbestos": "amiante",
    "pcb": "PCB (polychlorobiphenyles)",
    "lead": "plomb",
    "hap": "HAP (hydrocarbures aromatiques polycycliques)",
    "radon": "radon",
}

RISK_EXPLANATIONS = {
    "low": "Le niveau de risque est faible. Aucune mesure urgente n'est necessaire.",
    "medium": "Le niveau de risque est modere. Des precautions sont recommandees.",
    "high": "Le niveau de risque est eleve. Des mesures doivent etre prises rapidement.",
    "critical": "Le niveau de risque est critique. Des mesures immediates sont requises.",
    "unknown": "Le niveau de risque n'a pas encore ete evalue.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_building_or_raise(db: AsyncSession, building_id) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_samples(db: AsyncSession, building_id) -> list[Sample]:
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


async def _get_actions(db: AsyncSession, building_id) -> list[ActionItem]:
    result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    return list(result.scalars().all())


def _detected_pollutants(samples: list[Sample]) -> dict[str, list[Sample]]:
    """Group positive samples by pollutant type."""
    groups: dict[str, list[Sample]] = {}
    for s in samples:
        if s.threshold_exceeded and s.pollutant_type:
            key = s.pollutant_type.lower()
            groups.setdefault(key, []).append(s)
    return groups


def _max_risk_level(samples: list[Sample]) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    best = "unknown"
    best_val = -1
    for s in samples:
        level = (s.risk_level or "low").lower()
        val = order.get(level, -1)
        if val > best_val:
            best_val = val
            best = level
    return best


def _record_communication(building_id, comm_type: str, audience: str | None, summary: str) -> None:
    key = str(building_id)
    entry = {
        "id": str(uuid.uuid4()),
        "communication_type": comm_type,
        "audience": audience,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
    }
    _communication_log.setdefault(key, []).append(entry)


# ---------------------------------------------------------------------------
# PPE mapping by work category (CFST 6503)
# ---------------------------------------------------------------------------

_PPE_BY_CATEGORY = {
    "minor": [
        PPERequirement(equipment="Masque FFP2", standard="EN 149", mandatory=True),
        PPERequirement(equipment="Combinaison jetable type 5/6", standard="EN 13982", mandatory=True),
        PPERequirement(equipment="Gants nitrile", standard="EN 374", mandatory=True),
    ],
    "medium": [
        PPERequirement(equipment="Masque FFP3", standard="EN 149", mandatory=True),
        PPERequirement(equipment="Combinaison jetable type 5/6", standard="EN 13982", mandatory=True),
        PPERequirement(equipment="Gants nitrile", standard="EN 374", mandatory=True),
        PPERequirement(equipment="Lunettes de protection", standard="EN 166", mandatory=True),
        PPERequirement(equipment="Surbottes", standard="EN 13832", mandatory=True),
    ],
    "major": [
        PPERequirement(equipment="Masque complet avec filtre P3", standard="EN 12941", mandatory=True),
        PPERequirement(equipment="Combinaison etanche type 5", standard="EN 13982", mandatory=True),
        PPERequirement(equipment="Gants nitrile doubles", standard="EN 374", mandatory=True),
        PPERequirement(equipment="Lunettes de protection etanches", standard="EN 166", mandatory=True),
        PPERequirement(equipment="Surbottes etanches", standard="EN 13832", mandatory=True),
        PPERequirement(equipment="Scotch etanche pour jonctions", standard="CFST 6503", mandatory=True),
    ],
}

_DECONTAMINATION_STEPS = [
    DecontaminationStep(step_number=1, description="Aspirer la combinaison avec un aspirateur THE (filtre HEPA)."),
    DecontaminationStep(
        step_number=2, description="Retirer les surbottes et les placer dans un sac a dechets amiante."
    ),
    DecontaminationStep(step_number=3, description="Retirer la combinaison en la roulant vers l'exterieur."),
    DecontaminationStep(step_number=4, description="Retirer les gants et les placer dans le sac a dechets."),
    DecontaminationStep(step_number=5, description="Retirer le masque en dernier, nettoyer ou jeter le filtre."),
    DecontaminationStep(step_number=6, description="Se laver les mains et le visage a l'eau courante."),
    DecontaminationStep(step_number=7, description="Fermer et etiqueter le sac de dechets contamines."),
]


# ---------------------------------------------------------------------------
# FN1: Occupant Notice
# ---------------------------------------------------------------------------


async def generate_occupant_notice(db: AsyncSession, building_id) -> OccupantNotice:
    """Generate a plain-language notice for building occupants."""
    building = await _get_building_or_raise(db, building_id)
    samples = await _get_samples(db, building_id)
    actions = await _get_actions(db, building_id)

    detected = _detected_pollutants(samples)
    risk_level = _max_risk_level(samples) if samples else "unknown"

    # Situation
    if detected:
        pollutant_names = [POLLUTANT_LABELS.get(p, p) for p in detected]
        situation = (
            f"Un diagnostic de polluants a ete realise dans le batiment situe au "
            f"{building.address}, {building.postal_code} {building.city}. "
            f"Les substances suivantes ont ete detectees au-dessus des seuils reglementaires : "
            f"{', '.join(pollutant_names)}."
        )
    else:
        situation = (
            f"Un diagnostic de polluants a ete realise dans le batiment situe au "
            f"{building.address}, {building.postal_code} {building.city}. "
            f"Aucune substance dangereuse n'a ete detectee au-dessus des seuils reglementaires."
        )

    # Risk explanation
    risk_explanation = RISK_EXPLANATIONS.get(risk_level, RISK_EXPLANATIONS["unknown"])

    # Precautions
    precautions: list[str] = []
    if "asbestos" in detected:
        precautions.append("Ne pas percer, poncer, casser ou gratter les materiaux contenant de l'amiante.")
        precautions.append("Signaler immediatement tout materiau endommage a la gestion de l'immeuble.")
    if "lead" in detected:
        precautions.append("Eviter le contact avec les surfaces peintes ecaillees contenant du plomb.")
        precautions.append("Se laver les mains apres tout contact avec des surfaces anciennes.")
    if "pcb" in detected:
        precautions.append("Ne pas toucher les joints de fenetre ou de facade potentiellement contamines.")
    if "radon" in detected:
        precautions.append("Aerer regulierement les locaux, notamment au sous-sol et au rez-de-chaussee.")
    if not precautions:
        precautions.append("Aucune precaution specifique n'est requise.")

    # Planned actions
    planned: list[str] = []
    for a in actions:
        if a.status in ("open", "in_progress"):
            planned.append(f"{a.title} (priorite: {a.priority})")
    if not planned:
        planned.append("Aucune action n'est actuellement planifiee.")

    # Contacts
    contacts = [
        "Gerance de l'immeuble (coordonnees habituelles)",
        "Diagnostiqueur en charge du dossier",
    ]

    # Sections
    sections = [
        OccupantNoticeSection(title="Situation", content=situation),
        OccupantNoticeSection(title="Explication du niveau de risque", content=risk_explanation),
        OccupantNoticeSection(title="Precautions", content="; ".join(precautions)),
        OccupantNoticeSection(title="Actions prevues", content="; ".join(planned)),
        OccupantNoticeSection(title="Contacts", content="; ".join(contacts)),
    ]

    _record_communication(building_id, "occupant_notice", None, f"Occupant notice - risk: {risk_level}")

    return OccupantNotice(
        building_id=building.id,
        generated_at=datetime.now(UTC),
        overall_risk_level=risk_level,
        sections=sections,
        situation=situation,
        risk_level_explanation=risk_explanation,
        precautions=precautions,
        planned_actions=planned,
        contacts=contacts,
    )


# ---------------------------------------------------------------------------
# FN2: Worker Safety Briefing
# ---------------------------------------------------------------------------


async def generate_worker_safety_briefing(db: AsyncSession, building_id) -> WorkerSafetyBriefing:
    """Generate a CFST 6503-aligned worker safety briefing."""
    building = await _get_building_or_raise(db, building_id)
    samples = await _get_samples(db, building_id)

    # Group samples by location (zone proxy)
    zones_map: dict[str, list[Sample]] = {}
    for s in samples:
        if s.threshold_exceeded:
            zone_key = s.location_floor or s.location_room or "Non specifie"
            zones_map.setdefault(zone_key, []).append(s)

    zone_briefings: list[ZoneBriefing] = []
    overall_category = "minor"
    category_order = {"minor": 0, "medium": 1, "major": 2}

    for zone_name, zone_samples in zones_map.items():
        pollutants_present = list({s.pollutant_type.lower() for s in zone_samples if s.pollutant_type})

        # Determine work category from CFST field or fallback
        zone_category = "minor"
        for s in zone_samples:
            cat = (s.cfst_work_category or "minor").lower()
            if category_order.get(cat, 0) > category_order.get(zone_category, 0):
                zone_category = cat

        if category_order.get(zone_category, 0) > category_order.get(overall_category, 0):
            overall_category = zone_category

        ppe = _PPE_BY_CATEGORY.get(zone_category, _PPE_BY_CATEGORY["minor"])

        restrictions: list[str] = []
        if zone_category == "major":
            restrictions.append("Zone confinee obligatoire avec sas de decontamination.")
            restrictions.append("Acces reserve aux travailleurs formes et certifies amiante.")
            restrictions.append("Mesures d'empoussierement obligatoires.")
        elif zone_category == "medium":
            restrictions.append("Zone delimitee avec signalisation amiante.")
            restrictions.append("Aspirateur THE obligatoire.")
        else:
            restrictions.append("Travaux limites, humidification recommandee.")

        zone_briefings.append(
            ZoneBriefing(
                zone=zone_name,
                pollutants_present=pollutants_present,
                work_category=zone_category,
                ppe_requirements=ppe,
                work_restrictions=restrictions,
            )
        )

    # If no zones with positive samples, provide a default
    if not zone_briefings:
        zone_briefings.append(
            ZoneBriefing(
                zone="Batiment entier",
                pollutants_present=[],
                work_category="minor",
                ppe_requirements=_PPE_BY_CATEGORY["minor"],
                work_restrictions=["Aucune restriction specifique identifiee."],
            )
        )

    emergency_procedures = [
        "En cas d'exposition accidentelle, quitter immediatement la zone contaminee.",
        "Retirer les vetements contamines et les placer dans un sac etanche.",
        "Se laver abondamment a l'eau courante.",
        "Contacter le responsable de chantier et le medecin du travail.",
        "Documenter l'incident dans le journal de chantier.",
        "Notifier la SUVA en cas d'exposition a l'amiante.",
    ]

    _record_communication(
        building_id,
        "worker_safety_briefing",
        None,
        f"Worker briefing - category: {overall_category}, zones: {len(zone_briefings)}",
    )

    return WorkerSafetyBriefing(
        building_id=building.id,
        generated_at=datetime.now(UTC),
        overall_work_category=overall_category,
        zones=zone_briefings,
        emergency_procedures=emergency_procedures,
        decontamination_steps=_DECONTAMINATION_STEPS,
        general_ppe=_PPE_BY_CATEGORY.get(overall_category, _PPE_BY_CATEGORY["minor"]),
    )


# ---------------------------------------------------------------------------
# FN3: Stakeholder Notification
# ---------------------------------------------------------------------------

_AUDIENCE_DETAIL_LEVEL = {
    "owner": "detailed",
    "tenant": "brief",
    "authority": "detailed",
    "insurer": "standard",
}


async def generate_stakeholder_notification(
    db: AsyncSession,
    building_id,
    audience: str,
) -> StakeholderNotification:
    """Generate audience-specific stakeholder notification."""
    valid_audiences = {"owner", "tenant", "authority", "insurer"}
    if audience not in valid_audiences:
        raise ValueError(f"Invalid audience: {audience}. Must be one of {valid_audiences}")

    building = await _get_building_or_raise(db, building_id)
    samples = await _get_samples(db, building_id)
    detected = _detected_pollutants(samples)
    risk_level = _max_risk_level(samples) if samples else "unknown"
    detail_level = _AUDIENCE_DETAIL_LEVEL[audience]

    pollutant_names = [POLLUTANT_LABELS.get(p, p) for p in detected]

    # Summary
    if detected:
        summary = (
            f"Notification concernant le batiment {building.address}, "
            f"{building.postal_code} {building.city}. "
            f"Polluants detectes : {', '.join(pollutant_names)}. "
            f"Niveau de risque global : {risk_level}."
        )
    else:
        summary = (
            f"Notification concernant le batiment {building.address}, "
            f"{building.postal_code} {building.city}. "
            f"Aucun polluant detecte au-dessus des seuils reglementaires."
        )

    # Key facts
    key_facts: list[str] = [
        f"Adresse : {building.address}, {building.postal_code} {building.city}",
        f"Annee de construction : {building.construction_year or 'inconnue'}",
    ]
    if detected:
        key_facts.append(f"Polluants detectes : {', '.join(pollutant_names)}")
        key_facts.append(f"Nombre d'echantillons positifs : {sum(len(v) for v in detected.values())}")
    key_facts.append(f"Niveau de risque global : {risk_level}")

    # Audience-specific implications and required actions
    implications: list[str] = []
    required_actions: list[StakeholderAction] = []
    timeline: str | None = None

    if audience == "owner":
        implications.append("En tant que proprietaire, vous etes responsable de la gestion des polluants.")
        if detected:
            implications.append("Des travaux d'assainissement pourraient etre necessaires avant toute renovation.")
            implications.append("Un plan d'elimination des dechets (PED) doit etre etabli.")
        required_actions.append(
            StakeholderAction(action="Prendre connaissance du rapport de diagnostic", priority="high")
        )
        if detected:
            required_actions.append(
                StakeholderAction(
                    action="Mandater un plan d'assainissement",
                    deadline="30 jours",
                    priority="high",
                )
            )
            required_actions.append(
                StakeholderAction(
                    action="Informer les occupants",
                    deadline="14 jours",
                    priority="high",
                )
            )
        timeline = "Diagnostic recu. Actions a planifier sous 30 jours." if detected else None

    elif audience == "tenant":
        if detected:
            implications.append("Des polluants ont ete identifies dans le batiment que vous occupez.")
            implications.append("Des mesures de precaution sont recommandees (voir notice occupant).")
        else:
            implications.append("Aucun risque particulier n'a ete identifie pour les occupants.")
        required_actions.append(
            StakeholderAction(action="Consulter la notice d'information aux occupants", priority="medium")
        )

    elif audience == "authority":
        implications.append("Ce rapport est transmis conformement aux obligations legales cantonales.")
        if detected:
            implications.append(f"Polluants reglementes detectes : {', '.join(pollutant_names)}.")
            if "asbestos" in detected:
                implications.append("Notification SUVA potentiellement requise (amiante detecte).")
        required_actions.append(StakeholderAction(action="Verifier la conformite du diagnostic", priority="high"))
        if "asbestos" in detected:
            required_actions.append(
                StakeholderAction(
                    action="Valider le plan d'elimination des dechets amiantiferes",
                    deadline="14 jours",
                    priority="high",
                )
            )
        timeline = "Delai de traitement : 14 jours ouvrables apres reception."

    elif audience == "insurer":
        implications.append("Ce rapport informe sur l'etat sanitaire du batiment assure.")
        if detected:
            implications.append("La presence de polluants peut impacter la valeur assurable et les primes.")
            implications.append(f"Risque global evalue a : {risk_level}.")
        required_actions.append(StakeholderAction(action="Mettre a jour le dossier d'assurance", priority="medium"))
        if risk_level in ("high", "critical"):
            required_actions.append(
                StakeholderAction(
                    action="Reevaluer la couverture et les franchises",
                    priority="high",
                )
            )

    _record_communication(
        building_id,
        "stakeholder_notification",
        audience,
        f"Stakeholder notification ({audience}) - risk: {risk_level}",
    )

    return StakeholderNotification(
        building_id=building.id,
        generated_at=datetime.now(UTC),
        audience=audience,
        summary=summary,
        key_facts=key_facts,
        implications=implications,
        required_actions=required_actions,
        timeline=timeline,
        detail_level=detail_level,
    )


# ---------------------------------------------------------------------------
# FN4: Communication Log
# ---------------------------------------------------------------------------


async def get_communication_log(db: AsyncSession, building_id) -> CommunicationLog:
    """Return history of all generated communications for audit trail."""
    # Validate building exists
    await _get_building_or_raise(db, building_id)

    key = str(building_id)
    raw_entries = _communication_log.get(key, [])

    entries = [
        CommunicationLogEntry(
            id=e["id"],
            communication_type=e["communication_type"],
            audience=e.get("audience"),
            generated_at=datetime.fromisoformat(e["generated_at"]),
            summary=e["summary"],
        )
        for e in raw_entries
    ]

    return CommunicationLog(
        building_id=building_id,
        total_count=len(entries),
        entries=entries,
    )
