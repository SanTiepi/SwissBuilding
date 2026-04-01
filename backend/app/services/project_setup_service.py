"""
BatiConnect - Project Setup Service

Generates pre-filled work project drafts from building dossier data.
The wizard flow: user picks intervention type -> system auto-populates scope,
obligations, and documents -> user adjusts -> create intervention.

This is the "Lancer un projet de travaux" feature (Boucle 3).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACTION_STATUS_OPEN
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intervention type -> pollutant mapping
# ---------------------------------------------------------------------------
_TYPE_TO_POLLUTANT: dict[str, str] = {
    "asbestos_removal": "asbestos",
    "pcb_removal": "pcb",
    "lead_removal": "lead",
    "hap_removal": "hap",
    "radon_mitigation": "radon",
    "pfas_remediation": "pfas",
}

# French labels for intervention types
INTERVENTION_TYPE_LABELS: dict[str, str] = {
    "asbestos_removal": "Désamiantage",
    "pcb_removal": "Décontamination PCB",
    "lead_removal": "Déplombage",
    "hap_removal": "Traitement HAP",
    "radon_mitigation": "Assainissement radon",
    "pfas_remediation": "Remédiation PFAS",
    "renovation": "Rénovation",
    "maintenance": "Maintenance",
    "other": "Autre",
}

# Required document types per intervention type
_REQUIRED_DOCS: dict[str, list[dict[str, str]]] = {
    "asbestos_removal": [
        {"type": "diagnostic_report", "label": "Rapport de diagnostic amiante"},
        {"type": "lab_report", "label": "Analyses de laboratoire"},
        {"type": "floor_plan", "label": "Plans des étages concernés"},
        {"type": "suva_notification", "label": "Notification SUVA"},
        {"type": "work_permit", "label": "Permis de travaux"},
        {"type": "waste_plan", "label": "Plan d'élimination des déchets"},
    ],
    "pcb_removal": [
        {"type": "diagnostic_report", "label": "Rapport de diagnostic PCB"},
        {"type": "lab_report", "label": "Analyses de laboratoire"},
        {"type": "floor_plan", "label": "Plans des étages concernés"},
        {"type": "waste_plan", "label": "Plan d'élimination des déchets"},
    ],
    "lead_removal": [
        {"type": "diagnostic_report", "label": "Rapport de diagnostic plomb"},
        {"type": "lab_report", "label": "Analyses de laboratoire"},
        {"type": "floor_plan", "label": "Plans des étages concernés"},
        {"type": "waste_plan", "label": "Plan d'élimination des déchets"},
    ],
    "hap_removal": [
        {"type": "diagnostic_report", "label": "Rapport de diagnostic HAP"},
        {"type": "lab_report", "label": "Analyses de laboratoire"},
        {"type": "floor_plan", "label": "Plans des étages concernés"},
    ],
    "radon_mitigation": [
        {"type": "diagnostic_report", "label": "Rapport de mesure radon"},
        {"type": "floor_plan", "label": "Plans des étages concernés"},
    ],
    "pfas_remediation": [
        {"type": "diagnostic_report", "label": "Rapport de diagnostic PFAS"},
        {"type": "lab_report", "label": "Analyses de laboratoire"},
        {"type": "floor_plan", "label": "Plans des étages concernés"},
    ],
    "renovation": [
        {"type": "diagnostic_report", "label": "Rapport de diagnostic polluants"},
        {"type": "floor_plan", "label": "Plans des étages"},
        {"type": "work_permit", "label": "Permis de construire"},
    ],
    "maintenance": [
        {"type": "floor_plan", "label": "Plans des zones concernées"},
    ],
    "other": [
        {"type": "floor_plan", "label": "Plans des zones concernées"},
    ],
}

# Regulatory requirements per intervention type
_REGULATORY_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "asbestos_removal": [
        {"ref": "OTConst Art. 60a, 82-86", "label": "Ordonnance sur les travaux de construction"},
        {"ref": "CFST 6503", "label": "Catégorie de travaux CFST (mineur/moyen/majeur)"},
        {"ref": "OLED", "label": "Élimination des déchets (type_b/type_e/spécial)"},
        {"ref": "SUVA", "label": "Notification SUVA obligatoire si amiante positif"},
    ],
    "pcb_removal": [
        {"ref": "ORRChim Annexe 2.15", "label": "Seuil PCB > 50 mg/kg"},
        {"ref": "OLED", "label": "Élimination des déchets spéciaux"},
    ],
    "lead_removal": [
        {"ref": "ORRChim Annexe 2.18", "label": "Seuil plomb > 5000 mg/kg"},
        {"ref": "OLED", "label": "Élimination des déchets spéciaux"},
    ],
    "hap_removal": [
        {"ref": "OLED", "label": "Élimination des déchets contenant des HAP"},
    ],
    "radon_mitigation": [
        {"ref": "ORaP Art. 110", "label": "Seuils radon : 300/1000 Bq/m³"},
    ],
    "pfas_remediation": [
        {"ref": "OSol/OEaux", "label": "Réglementation sur les PFAS (émergente)"},
    ],
    "renovation": [
        {"ref": "OTConst", "label": "Vérification polluants avant travaux de rénovation"},
    ],
    "maintenance": [],
    "other": [],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_project_draft(
    db: AsyncSession,
    building_id: UUID,
    intervention_type: str,
    created_by_id: UUID,
) -> dict:
    """Generate a pre-filled project/intervention draft from building dossier.

    Pulls from building data:
    - Relevant zones for the intervention type
    - Materials/elements that need work (from diagnostics)
    - Applicable regulatory requirements
    - Required documents/pieces
    - Existing diagnostics covering the scope
    - Open actions related to this type

    Returns a structured draft with all sections pre-populated.
    """
    # 0. Verify building exists
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    pollutant = _TYPE_TO_POLLUTANT.get(intervention_type)
    label = INTERVENTION_TYPE_LABELS.get(intervention_type, intervention_type)

    # 1. Load diagnostics
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    # 2. Load samples (positive ones are key for scope)
    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # 3. Load zones
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    # 4. Load documents
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    # 5. Load open actions
    action_result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == ACTION_STATUS_OPEN,
            )
        )
    )
    open_actions = list(action_result.scalars().all())

    # --- Build scope ---
    scope = _build_scope(samples, zones, pollutant, intervention_type)

    # --- Build document checklist ---
    doc_checklist = _build_document_checklist(documents, diagnostics, intervention_type)

    # --- Build regulatory requirements ---
    regulatory_requirements = _REGULATORY_REQUIREMENTS.get(intervention_type, [])

    # --- Relevant diagnostics ---
    relevant_diagnostics = _find_relevant_diagnostics(diagnostics, pollutant)

    # --- Related open actions ---
    related_actions = _find_related_actions(open_actions, pollutant, intervention_type)

    # --- Gap analysis ---
    gap = _compute_gap_analysis(doc_checklist, scope, diagnostics, pollutant)

    # --- Title suggestion ---
    building_name = building.address or f"Bâtiment {str(building_id)[:8]}"
    suggested_title = f"{label} — {building_name}"

    return {
        "building_id": str(building_id),
        "suggested_title": suggested_title,
        "intervention_type": intervention_type,
        "intervention_type_label": label,
        "scope": scope,
        "regulatory_requirements": regulatory_requirements,
        "document_checklist": doc_checklist,
        "relevant_diagnostics": [
            {
                "id": str(d.id),
                "diagnostic_type": d.diagnostic_type,
                "status": d.status,
                "date_inspection": d.date_inspection.isoformat() if d.date_inspection else None,
                "laboratory": d.laboratory,
            }
            for d in relevant_diagnostics
        ],
        "related_actions": [
            {
                "id": str(a.id),
                "title": a.title,
                "priority": a.priority,
                "action_type": a.action_type,
            }
            for a in related_actions
        ],
        "gap_analysis": gap,
        "generated_at": datetime.now(UTC).isoformat(),
    }


async def create_project_from_wizard(
    db: AsyncSession,
    building_id: UUID,
    project_data: dict,
    created_by_id: UUID,
) -> Intervention:
    """Create an Intervention from the wizard data.

    Links to building, sets up zones_affected and materials_used from scope,
    and creates action items for identified gaps.
    """
    # Verify building
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # Extract fields
    zones_affected = project_data.get("zones_affected")
    materials_used = project_data.get("materials_used")

    intervention = Intervention(
        building_id=building_id,
        intervention_type=project_data["intervention_type"],
        title=project_data["title"],
        description=project_data.get("description"),
        status="planned",
        zones_affected=zones_affected,
        materials_used=materials_used,
        created_by=created_by_id,
    )
    db.add(intervention)

    # Create action items for identified gaps
    gaps = project_data.get("gaps", [])
    for gap_item in gaps:
        action = ActionItem(
            building_id=building_id,
            title=gap_item.get("label", "Pièce manquante"),
            description=f"Requis pour le projet: {project_data['title']}",
            action_type="documentation",
            source_type="system",
            priority="high",
            status=ACTION_STATUS_OPEN,
            created_by=created_by_id,
        )
        db.add(action)

    await db.flush()  # get intervention.id before commit

    # Create a BuildingCase wrapping this intervention (V3 doctrine: BuildingCase = operating root)
    org_id = project_data.get("organization_id") or building.organization_id
    case = BuildingCase(
        building_id=building_id,
        organization_id=org_id,
        created_by_id=created_by_id,
        case_type="works",
        title=project_data["title"],
        description=project_data.get("description"),
        state="in_preparation",
        intervention_id=intervention.id,
        pollutant_scope=project_data.get("pollutant_scope"),
        spatial_scope_ids=project_data.get("spatial_scope_ids"),
        priority=project_data.get("priority", "medium"),
    )
    db.add(case)

    await db.commit()
    await db.refresh(intervention)
    return intervention


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_scope(
    samples: list[Sample],
    zones: list[Zone],
    pollutant: str | None,
    intervention_type: str,
) -> dict:
    """Build the auto-detected scope from diagnostics and zones."""
    # Filter positive samples for the pollutant
    if pollutant:
        relevant_samples = [
            s for s in samples if (s.pollutant_type or "").lower() == pollutant.lower() and s.threshold_exceeded
        ]
    else:
        # For renovation/maintenance/other, show all positive samples
        relevant_samples = [s for s in samples if s.threshold_exceeded]

    # Extract affected zones from sample locations
    affected_floors: set[str] = set()
    affected_rooms: set[str] = set()
    affected_materials: dict[str, list[dict]] = defaultdict(list)
    elements_to_treat: list[dict] = []

    for s in relevant_samples:
        if s.location_floor:
            affected_floors.add(s.location_floor)
        if s.location_room:
            affected_rooms.add(s.location_room)

        mat_key = s.material_category or "Inconnu"
        material_info = {
            "sample_id": str(s.id),
            "material_description": s.material_description,
            "material_state": s.material_state,
            "concentration": s.concentration,
            "unit": s.unit,
            "risk_level": s.risk_level,
            "location": f"{s.location_floor or ''} - {s.location_room or ''}".strip(" -"),
            "pollutant_type": s.pollutant_type,
        }
        affected_materials[mat_key].append(material_info)

        elements_to_treat.append(
            {
                "sample_number": s.sample_number,
                "location": f"{s.location_floor or ''} - {s.location_room or ''}".strip(" -"),
                "material": s.material_description or s.material_category or "Inconnu",
                "risk_level": s.risk_level or "unknown",
                "concentration": s.concentration,
                "unit": s.unit,
                "pollutant_type": s.pollutant_type,
                "cfst_work_category": s.cfst_work_category,
                "waste_disposal_type": s.waste_disposal_type,
            }
        )

    # Match zones from building zones model
    matched_zones = []
    for z in zones:
        floor_str = str(z.floor_number) if z.floor_number is not None else None
        name_lower = (z.name or "").lower()
        # Match by floor number or if zone name matches a room
        if floor_str in affected_floors or any(room.lower() in name_lower for room in affected_rooms if room):
            matched_zones.append(
                {
                    "id": str(z.id),
                    "name": z.name,
                    "zone_type": z.zone_type,
                    "floor_number": z.floor_number,
                    "surface_area_m2": z.surface_area_m2,
                }
            )

    return {
        "zones": matched_zones,
        "elements_to_treat": elements_to_treat,
        "materials_involved": {
            category: {
                "count": len(items),
                "items": items,
            }
            for category, items in affected_materials.items()
        },
        "affected_floors": sorted(affected_floors),
        "affected_rooms": sorted(affected_rooms),
        "total_positive_samples": len(relevant_samples),
        "pollutants_found": sorted({(s.pollutant_type or "unknown") for s in relevant_samples}),
    }


def _build_document_checklist(
    documents: list[Document],
    diagnostics: list[Diagnostic],
    intervention_type: str,
) -> list[dict]:
    """Build required documents checklist with existing/missing status."""
    required = _REQUIRED_DOCS.get(intervention_type, [])
    doc_types_present = {(d.document_type or "").lower() for d in documents}

    # Reports count as diagnostic_report
    if any(d.status in ("completed", "validated") for d in diagnostics):
        doc_types_present.add("diagnostic_report")

    checklist = []
    for req in required:
        req_type = req["type"].lower()
        # Flexible matching: floor_plan matches plan too
        found = req_type in doc_types_present
        if not found and req_type == "floor_plan":
            found = "plan" in doc_types_present or "floor_plan" in doc_types_present
        if not found and req_type == "lab_report":
            found = "lab_report" in doc_types_present or "lab_analysis" in doc_types_present

        checklist.append(
            {
                "document_type": req["type"],
                "label": req["label"],
                "status": "available" if found else "missing",
            }
        )

    return checklist


def _find_relevant_diagnostics(
    diagnostics: list[Diagnostic],
    pollutant: str | None,
) -> list[Diagnostic]:
    """Find diagnostics relevant to the intervention type."""
    if pollutant:
        relevant = [d for d in diagnostics if (d.diagnostic_type or "").lower() == pollutant.lower()]
        if relevant:
            return relevant
    # Fallback: return all completed/validated diagnostics
    return [d for d in diagnostics if d.status in ("completed", "validated")]


def _find_related_actions(
    open_actions: list[ActionItem],
    pollutant: str | None,
    intervention_type: str,
) -> list[ActionItem]:
    """Find open actions related to this project type."""
    related = []
    for a in open_actions:
        title_lower = (a.title or "").lower()
        meta = a.metadata_json or {}
        meta_pollutant = (meta.get("pollutant") or "").lower()

        # Match by pollutant
        if pollutant and (pollutant.lower() in title_lower or pollutant.lower() == meta_pollutant):
            related.append(a)
            continue

        # Match by action type for remediation actions
        if a.action_type in ("remediation", "investigation", "procurement"):
            related.append(a)

    return related


def _compute_gap_analysis(
    doc_checklist: list[dict],
    scope: dict,
    diagnostics: list[Diagnostic],
    pollutant: str | None,
) -> dict:
    """Compute what's missing to start the project."""
    missing_docs = [d for d in doc_checklist if d["status"] == "missing"]
    total_docs = len(doc_checklist)
    available_docs = total_docs - len(missing_docs)

    # Check if we have relevant diagnostics
    has_diagnostic = any(d.status in ("completed", "validated") for d in diagnostics)
    has_pollutant_diagnostic = False
    if pollutant:
        has_pollutant_diagnostic = any(
            (d.diagnostic_type or "").lower() == pollutant.lower() and d.status in ("completed", "validated")
            for d in diagnostics
        )

    has_positive_samples = scope.get("total_positive_samples", 0) > 0

    # Readiness estimation
    blockers: list[str] = []
    if not has_diagnostic:
        blockers.append("Aucun diagnostic complété")
    if pollutant and not has_pollutant_diagnostic:
        blockers.append(f"Pas de diagnostic {pollutant} validé")
    for doc in missing_docs:
        blockers.append(f"Manque: {doc['label']}")

    can_start = len(blockers) == 0
    readiness_score = available_docs / total_docs if total_docs > 0 else 0.0

    return {
        "can_start": can_start,
        "readiness_score": round(readiness_score, 2),
        "missing_documents_count": len(missing_docs),
        "available_documents_count": available_docs,
        "total_required_documents": total_docs,
        "has_diagnostic": has_diagnostic,
        "has_pollutant_diagnostic": has_pollutant_diagnostic,
        "has_positive_samples": has_positive_samples,
        "blockers": blockers,
        "message": (
            "Vous pouvez démarrer ce projet"
            if can_start
            else f"Il manque {len(blockers)} élément(s) avant de pouvoir démarrer"
        ),
    }
