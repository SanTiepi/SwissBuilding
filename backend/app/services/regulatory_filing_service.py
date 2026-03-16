"""Regulatory filing service for Swiss building pollutant declarations.

Covers:
- SUVA asbestos notification (CFST 6503)
- Cantonal pollutant declarations (VD/GE format differences)
- OLED waste tracking manifests
- Filing status tracking
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.regulatory_filing import (
    CantonalDeclaration,
    ContractorInfo,
    DiagnosticReference,
    DisposalFacility,
    FilingStatus,
    FilingTypeStatus,
    PollutantLocation,
    ResponsibleParty,
    SafetyMeasure,
    SuvaNotification,
    TransportChainStep,
    WasteEntry,
    WasteManifest,
)

# CFST 6503 work category hierarchy (higher = more dangerous)
_WORK_CATEGORY_RANK = {"minor": 1, "medium": 2, "major": 3}

# CFST 6503 safety measures by work category
_SAFETY_MEASURES: dict[str, list[dict[str, str]]] = {
    "minor": [
        {
            "category": "protection_individuelle",
            "description": "Masque FFP3, combinaison jetable, gants",
            "cfst_reference": "CFST 6503 §4.1",
        },
        {
            "category": "aspiration",
            "description": "Aspiration locale avec filtre HEPA",
            "cfst_reference": "CFST 6503 §4.2",
        },
    ],
    "medium": [
        {
            "category": "protection_individuelle",
            "description": "Masque à ventilation assistée, combinaison intégrale jetable",
            "cfst_reference": "CFST 6503 §5.1",
        },
        {
            "category": "confinement",
            "description": "Zone de travail confinée avec sas",
            "cfst_reference": "CFST 6503 §5.2",
        },
        {
            "category": "decontamination",
            "description": "Unité de décontamination avec douche",
            "cfst_reference": "CFST 6503 §5.3",
        },
        {
            "category": "aspiration",
            "description": "Extracteur à dépression avec filtre HEPA",
            "cfst_reference": "CFST 6503 §5.4",
        },
    ],
    "major": [
        {
            "category": "protection_individuelle",
            "description": "Appareil respiratoire isolant ou masque ventilation assistée TM3P",
            "cfst_reference": "CFST 6503 §6.1",
        },
        {
            "category": "confinement",
            "description": "Confinement complet étanche avec dépression contrôlée",
            "cfst_reference": "CFST 6503 §6.2",
        },
        {
            "category": "decontamination",
            "description": "Unité de décontamination 5 compartiments",
            "cfst_reference": "CFST 6503 §6.3",
        },
        {
            "category": "mesures_air",
            "description": "Mesures d'empoussièrement en continu (PCM/META)",
            "cfst_reference": "CFST 6503 §6.4",
        },
        {
            "category": "notification",
            "description": "Notification SUVA obligatoire 14 jours avant travaux",
            "cfst_reference": "CFST 6503 §6.5",
        },
    ],
}

# Default estimated days per work category
_DURATION_DAYS = {"minor": 5, "medium": 15, "major": 30}


async def _get_building_or_raise(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    result = await db.execute(
        select(Diagnostic).where(Diagnostic.building_id == building_id).options(selectinload(Diagnostic.samples))
    )
    return list(result.scalars().unique().all())


async def _get_asbestos_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.pollutant_type.in_(["asbestos", "amiante"]),
        )
    )
    return list(result.scalars().all())


async def _get_all_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


async def _get_planned_intervention(db: AsyncSession, building_id: UUID) -> Intervention | None:
    result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id, Intervention.status == "planned")
        .order_by(Intervention.date_start)
        .limit(1)
    )
    return result.scalar_one_or_none()


def _max_work_category(samples: list[Sample]) -> str | None:
    """Determine the highest CFST 6503 work category from samples."""
    best: str | None = None
    best_rank = 0
    for s in samples:
        cat = s.cfst_work_category
        if cat and _WORK_CATEGORY_RANK.get(cat, 0) > best_rank:
            best = cat
            best_rank = _WORK_CATEGORY_RANK[cat]
    return best


def _get_safety_measures(work_category: str | None) -> list[SafetyMeasure]:
    if not work_category or work_category not in _SAFETY_MEASURES:
        return []
    return [SafetyMeasure(**m) for m in _SAFETY_MEASURES[work_category]]


async def generate_suva_notification(db: AsyncSession, building_id: UUID) -> SuvaNotification:
    """Generate SUVA asbestos notification data (CFST 6503).

    Gathers building info, asbestos sample locations, determines work category,
    and assembles contractor/safety information for SUVA form filling.
    """
    building = await _get_building_or_raise(db, building_id)
    asbestos_samples = await _get_asbestos_samples(db, building_id)
    diagnostics = await _get_diagnostics(db, building_id)
    intervention = await _get_planned_intervention(db, building_id)

    pollutant_locations = [
        PollutantLocation(
            sample_id=s.id,
            pollutant_type=s.pollutant_type,
            location=" / ".join(filter(None, [s.location_floor, s.location_room, s.location_detail])) or None,
            material_description=s.material_description,
            material_state=s.material_state,
            concentration=s.concentration,
            unit=s.unit,
            cfst_work_category=s.cfst_work_category,
            risk_level=s.risk_level,
        )
        for s in asbestos_samples
    ]

    max_cat = _max_work_category(asbestos_samples)
    safety = _get_safety_measures(max_cat)
    duration = _DURATION_DAYS.get(max_cat, 10) if max_cat else None

    contractor = None
    if intervention:
        contractor = ContractorInfo(
            contractor_name=intervention.contractor_name,
            contractor_id=intervention.contractor_id,
            intervention_type=intervention.intervention_type,
            date_start=str(intervention.date_start) if intervention.date_start else None,
            date_end=str(intervention.date_end) if intervention.date_end else None,
        )

    suva_required = any(d.suva_notification_required for d in diagnostics) or len(asbestos_samples) > 0

    diag_refs = [
        f"{d.diagnostic_type} #{d.laboratory_report_number or str(d.id)[:8]}"
        for d in diagnostics
        if d.status in ("completed", "validated")
    ]

    return SuvaNotification(
        building_id=building_id,
        address=building.address,
        postal_code=building.postal_code,
        city=building.city,
        canton=building.canton,
        construction_year=building.construction_year,
        pollutant_locations=pollutant_locations,
        max_work_category=max_cat,
        estimated_duration_days=duration,
        contractor=contractor,
        safety_measures=safety,
        suva_notification_required=suva_required,
        diagnostic_references=diag_refs,
        generated_at=datetime.now(UTC),
    )


# Canton-specific configuration
_CANTON_CONFIG: dict[str, dict] = {
    "VD": {
        "format_variant": "VD",
        "required_fields": [
            "adresse_complete",
            "annee_construction",
            "type_polluants",
            "resultats_analyses",
            "laboratoire_agree",
            "numero_rapport",
            "mesures_prevues",
            "calendrier_travaux",
            "entreprise_assainissement",
        ],
        "compliance_commitments": [
            "Respect de la Directive cantonale VD sur l'amiante dans les bâtiments",
            "Notification au Service de l'environnement (SEVEN) avant travaux",
            "Élimination conforme OLED via filière agréée",
            "Rapport de fin de travaux avec mesures libératoires",
        ],
        "canton_specific_notes": [
            "Canton de Vaud: déclaration au SEVEN obligatoire",
            "Formulaire VD spécifique requis pour travaux d'assainissement",
            "Contrôle libératoire par laboratoire accrédité exigé",
        ],
    },
    "GE": {
        "format_variant": "GE",
        "required_fields": [
            "adresse_complete",
            "annee_construction",
            "type_polluants",
            "resultats_analyses",
            "laboratoire_agree",
            "numero_rapport",
            "plan_assainissement",
            "entreprise_certifiee_FACH",
            "calendrier_travaux",
            "plan_gestion_dechets",
        ],
        "compliance_commitments": [
            "Respect du Règlement genevois sur la gestion des déchets (RGD)",
            "Notification au Service de toxicologie de l'environnement bâti (STEB)",
            "Entreprise certifiée FACH pour travaux amiante",
            "Plan de gestion des déchets de chantier (PGDC) obligatoire",
            "Mesures libératoires par organisme accrédité",
        ],
        "canton_specific_notes": [
            "Canton de Genève: déclaration au STEB obligatoire",
            "Certification FACH exigée pour entreprise d'assainissement",
            "PGDC obligatoire pour tout chantier avec polluants",
        ],
    },
}

_DEFAULT_CANTON_CONFIG: dict = {
    "format_variant": "standard",
    "required_fields": [
        "adresse_complete",
        "annee_construction",
        "type_polluants",
        "resultats_analyses",
        "laboratoire_agree",
        "numero_rapport",
        "mesures_prevues",
    ],
    "compliance_commitments": [
        "Respect de l'OTConst Art. 60a, 82-86",
        "Élimination conforme OLED",
        "Notification SUVA si amiante détecté",
    ],
    "canton_specific_notes": [],
}


async def generate_cantonal_declaration(
    db: AsyncSession, building_id: UUID, canton: str | None = None
) -> CantonalDeclaration:
    """Generate canton-specific pollutant declaration.

    VD and GE have specific format requirements; other cantons get a standard format.
    Canton defaults to the building's canton if not provided.
    """
    building = await _get_building_or_raise(db, building_id)
    effective_canton = (canton or building.canton).upper()
    diagnostics = await _get_diagnostics(db, building_id)
    all_samples = await _get_all_samples(db, building_id)

    config = _CANTON_CONFIG.get(effective_canton, _DEFAULT_CANTON_CONFIG)

    # Pollutant summary: count samples per pollutant type
    pollutant_summary: dict[str, int] = {}
    for s in all_samples:
        ptype = s.pollutant_type or "unknown"
        pollutant_summary[ptype] = pollutant_summary.get(ptype, 0) + 1

    diag_refs = [
        DiagnosticReference(
            diagnostic_id=d.id,
            diagnostic_type=d.diagnostic_type,
            status=d.status,
            date_report=str(d.date_report) if d.date_report else None,
            laboratory=d.laboratory,
            laboratory_report_number=d.laboratory_report_number,
        )
        for d in diagnostics
    ]

    return CantonalDeclaration(
        building_id=building_id,
        canton=effective_canton,
        format_variant=config["format_variant"],
        address=building.address,
        postal_code=building.postal_code,
        city=building.city,
        construction_year=building.construction_year,
        pollutant_summary=pollutant_summary,
        required_fields=config["required_fields"],
        diagnostic_references=diag_refs,
        compliance_commitments=config["compliance_commitments"],
        canton_specific_notes=config["canton_specific_notes"],
        generated_at=datetime.now(UTC),
    )


# OLED waste category descriptions
_WASTE_DESCRIPTIONS = {
    "type_b": "Matériaux inertes / déchets de construction propres",
    "type_e": "Déchets contrôlés (HAP, PCB ≤ 50 mg/kg, plomb ≤ 5000 mg/kg)",
    "special": "Déchets spéciaux (amiante, PCB > 50 mg/kg, plomb > 5000 mg/kg)",
}

_DISPOSAL_FACILITIES = {
    "type_b": DisposalFacility(
        facility_type="Décharge de type B (matériaux inertes)",
        waste_categories_accepted=["type_b"],
    ),
    "type_e": DisposalFacility(
        facility_type="Décharge de type E (déchets contrôlés)",
        waste_categories_accepted=["type_e"],
    ),
    "special": DisposalFacility(
        facility_type="Installation d'élimination agréée (déchets spéciaux)",
        waste_categories_accepted=["special"],
    ),
}


def _classify_sample_waste(sample: Sample) -> str:
    """Classify a sample into OLED waste category."""
    ptype = (sample.pollutant_type or "").lower()
    conc = sample.concentration
    if ptype in ("asbestos", "amiante"):
        return "special"
    if ptype == "pcb" and conc is not None and conc > 50:
        return "special"
    if ptype in ("lead", "plomb") and conc is not None and conc > 5000:
        return "special"
    if ptype == "hap":
        return "type_e"
    if ptype == "pcb" and conc is not None and conc <= 50:
        return "type_e"
    if ptype in ("lead", "plomb") and conc is not None and conc <= 5000:
        return "type_e"
    return "type_b"


async def generate_waste_manifest(db: AsyncSession, building_id: UUID) -> WasteManifest:
    """Generate OLED waste tracking manifest.

    Includes waste categories, estimated volumes, disposal facilities,
    transport chain, responsible parties, and auto-generated tracking number.
    """
    building = await _get_building_or_raise(db, building_id)
    all_samples = await _get_all_samples(db, building_id)
    intervention = await _get_planned_intervention(db, building_id)

    tracking_number = f"WM-{str(uuid4())[:8].upper()}"

    # Aggregate waste entries by category
    category_samples: dict[str, list[Sample]] = {}
    for s in all_samples:
        cat = _classify_sample_waste(s)
        category_samples.setdefault(cat, []).append(s)

    waste_entries: list[WasteEntry] = []
    for cat in ("type_b", "type_e", "special"):
        samples_in_cat = category_samples.get(cat, [])
        if not samples_in_cat and cat == "type_b" and not category_samples:
            # Default entry for buildings with no samples
            waste_entries.append(
                WasteEntry(
                    waste_category=cat,
                    description=_WASTE_DESCRIPTIONS[cat],
                )
            )
            continue
        if not samples_in_cat:
            continue
        locations = []
        for s in samples_in_cat:
            loc = " / ".join(filter(None, [s.location_floor, s.location_room, s.location_detail]))
            if loc:
                locations.append(loc)
        waste_entries.append(
            WasteEntry(
                waste_category=cat,
                description=_WASTE_DESCRIPTIONS[cat],
                estimated_volume_m3=round(len(samples_in_cat) * 0.5, 1),
                estimated_weight_tons=round(len(samples_in_cat) * 0.5 * 1.3, 2),
                source_location="; ".join(locations[:5]) if locations else None,
            ),
        )

    # If no entries at all (no samples), add a default type_b
    if not waste_entries:
        waste_entries.append(
            WasteEntry(
                waste_category="type_b",
                description=_WASTE_DESCRIPTIONS["type_b"],
            )
        )

    # Disposal facilities for categories present
    categories_present = {e.waste_category for e in waste_entries}
    facilities = [_DISPOSAL_FACILITIES[cat] for cat in ("type_b", "type_e", "special") if cat in categories_present]

    # Transport chain
    transport_chain = [
        TransportChainStep(
            step_number=1,
            description="Collecte et conditionnement sur site",
            requirements=["Tri par catégorie OLED", "Étiquetage réglementaire"],
        ),
        TransportChainStep(
            step_number=2,
            description="Transport vers installation d'élimination",
            requirements=["Bordereau de suivi des déchets", "Transporteur agréé"],
        ),
        TransportChainStep(
            step_number=3,
            description="Réception et élimination",
            requirements=["Attestation d'élimination", "Archivage 10 ans minimum"],
        ),
    ]
    if "special" in categories_present:
        transport_chain[1].requirements.append("ADR pour déchets spéciaux")
        transport_chain[1].requirements.append("Bordereau LMD (mouvement déchets spéciaux)")

    # Responsible parties
    responsible_parties = [
        ResponsibleParty(role="maître_ouvrage", name=None, contact_id=building.owner_id or building.created_by),
    ]
    if intervention and intervention.contractor_name:
        responsible_parties.append(
            ResponsibleParty(
                role="entreprise_assainissement",
                name=intervention.contractor_name,
                contact_id=intervention.contractor_id,
            )
        )

    return WasteManifest(
        building_id=building_id,
        tracking_number=tracking_number,
        waste_entries=waste_entries,
        disposal_facilities=facilities,
        transport_chain=transport_chain,
        responsible_parties=responsible_parties,
        regulatory_references=[
            "OLED (Ordonnance sur la limitation et l'élimination des déchets)",
            "ORRChim Annexe 2.15 (PCB: seuil 50 mg/kg)",
            "ORRChim Annexe 2.18 (Plomb: seuil 5000 mg/kg)",
            "LMD (Mouvement des déchets spéciaux)",
        ],
        generated_at=datetime.now(UTC),
    )


async def get_filing_status(db: AsyncSession, building_id: UUID) -> FilingStatus:
    """Determine which regulatory filings are needed, done, or overdue.

    Checks:
    - SUVA notification: required if asbestos found
    - Cantonal declaration: required if any pollutant found
    - Waste manifest: required if any hazardous/controlled waste
    """
    building = await _get_building_or_raise(db, building_id)
    diagnostics = await _get_diagnostics(db, building_id)
    all_samples = await _get_all_samples(db, building_id)

    filings: list[FilingTypeStatus] = []

    # --- SUVA notification ---
    has_asbestos = any(s.pollutant_type in ("asbestos", "amiante") for s in all_samples)
    suva_required_by_diag = any(d.suva_notification_required for d in diagnostics)
    suva_required = has_asbestos or suva_required_by_diag
    suva_completed = any(d.suva_notification_date is not None for d in diagnostics)
    suva_overdue = suva_required and not suva_completed

    filings.append(
        FilingTypeStatus(
            filing_type="suva_notification",
            required=suva_required,
            reason="Présence d'amiante détectée"
            if has_asbestos
            else ("Notification SUVA requise par diagnostic" if suva_required_by_diag else None),
            completed=suva_completed,
            completed_date=next((str(d.suva_notification_date) for d in diagnostics if d.suva_notification_date), None),
            overdue=suva_overdue,
            next_action="Soumettre notification SUVA (14 jours avant travaux)" if suva_overdue else None,
        )
    )

    # --- Cantonal declaration ---
    has_pollutants = len(all_samples) > 0
    canton_completed = any(d.canton_notification_date is not None for d in diagnostics)
    canton_overdue = has_pollutants and not canton_completed

    filings.append(
        FilingTypeStatus(
            filing_type="cantonal_declaration",
            required=has_pollutants,
            reason=f"Polluants détectés ({len(all_samples)} échantillons)" if has_pollutants else None,
            completed=canton_completed,
            completed_date=next(
                (str(d.canton_notification_date) for d in diagnostics if d.canton_notification_date), None
            ),
            overdue=canton_overdue,
            next_action=(f"Soumettre déclaration cantonale ({building.canton})" if canton_overdue else None),
        )
    )

    # --- Waste manifest ---
    has_hazardous = any(_classify_sample_waste(s) in ("type_e", "special") for s in all_samples)
    # Waste manifest is never auto-completed in the system, always pending if required
    waste_overdue = has_hazardous

    filings.append(
        FilingTypeStatus(
            filing_type="waste_manifest",
            required=has_hazardous,
            reason="Déchets contrôlés ou spéciaux identifiés" if has_hazardous else None,
            completed=False,
            overdue=waste_overdue,
            next_action="Générer bordereau OLED et planifier élimination" if waste_overdue else None,
        )
    )

    total_required = sum(1 for f in filings if f.required)
    total_completed = sum(1 for f in filings if f.required and f.completed)
    total_overdue = sum(1 for f in filings if f.overdue)

    return FilingStatus(
        building_id=building_id,
        filings=filings,
        total_required=total_required,
        total_completed=total_completed,
        total_overdue=total_overdue,
        generated_at=datetime.now(UTC),
    )
