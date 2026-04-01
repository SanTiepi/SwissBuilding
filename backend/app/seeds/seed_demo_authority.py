"""
SwissBuildingOS - Authority-Ready Demo Seed

Takes one seeded building and completes it with all the data needed
to demonstrate a full compliance journey:
- Complete diagnostic with all 5 pollutants
- Positive asbestos and PCB samples with classifications
- SUVA notification filed
- CFST work category assigned
- Waste disposal classified
- Compliance artefacts (SUVA notification, cantonal form)
- Planned and completed interventions
- Post-works states generated
- Readiness evaluations run
- Trust score computed
- Unknown issues detected
- Change signals generated
- Contradiction detection run

Idempotent: can be run multiple times safely.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# Stable UUIDs for idempotency
_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
_SAMPLE_IDS = {
    "asbestos": uuid.uuid5(_NS, "authority-demo-sample-asbestos"),
    "pcb": uuid.uuid5(_NS, "authority-demo-sample-pcb"),
    "lead": uuid.uuid5(_NS, "authority-demo-sample-lead"),
    "hap": uuid.uuid5(_NS, "authority-demo-sample-hap"),
    "radon": uuid.uuid5(_NS, "authority-demo-sample-radon"),
}
_ARTEFACT_IDS = {
    "suva": uuid.uuid5(_NS, "authority-demo-artefact-suva"),
    "cantonal": uuid.uuid5(_NS, "authority-demo-artefact-cantonal"),
}
_INTERVENTION_IDS = {
    "asbestos_removal": uuid.uuid5(_NS, "authority-demo-intervention-asbestos"),
    "pcb_removal": uuid.uuid5(_NS, "authority-demo-intervention-pcb"),
}
_DOCUMENT_IDS = {
    "diagnostic_report": uuid.uuid5(_NS, "authority-demo-doc-diag-report"),
    "suva_notification": uuid.uuid5(_NS, "authority-demo-doc-suva-notif"),
    "waste_elimination_plan": uuid.uuid5(_NS, "authority-demo-doc-waste-plan"),
}


async def _find_target_building(db: AsyncSession) -> tuple[Building, Diagnostic] | None:
    """Find the first building that has a diagnostic."""
    stmt = (
        select(Building, Diagnostic)
        .join(Diagnostic, Diagnostic.building_id == Building.id)
        .order_by(Building.created_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return row[0], row[1]


async def _ensure_samples(db: AsyncSession, diagnostic_id: uuid.UUID) -> dict[str, Sample]:
    """Create samples for all 5 pollutants if they don't exist."""
    sample_specs = [
        {
            "id": _SAMPLE_IDS["asbestos"],
            "diagnostic_id": diagnostic_id,
            "sample_number": "AUTH-DEMO-001",
            "location_floor": "Sous-sol",
            "location_room": "Sous-sol",
            "location_detail": "Flocage sur structure métallique",
            "material_category": "flocage",
            "material_description": "Flocage fibreux gris-blanc",
            "material_state": "friable",
            "pollutant_type": "asbestos",
            "pollutant_subtype": "chrysotile",
            "concentration": 15.0,
            "unit": "%",
            "threshold_exceeded": True,
            "risk_level": "high",
            "cfst_work_category": "major",
            "action_required": "Désamiantage complet",
            "waste_disposal_type": "special",
        },
        {
            "id": _SAMPLE_IDS["pcb"],
            "diagnostic_id": diagnostic_id,
            "sample_number": "AUTH-DEMO-002",
            "location_floor": "1er étage",
            "location_room": "Cuisine",
            "location_detail": "Joint d'étanchéité entre panneaux",
            "material_category": "joint",
            "material_description": "Mastic d'étanchéité gris-noir",
            "material_state": "degraded",
            "pollutant_type": "pcb",
            "concentration": 120.0,
            "unit": "mg/kg",
            "threshold_exceeded": True,
            "risk_level": "medium",
            "action_required": "Retrait joints PCB",
            "waste_disposal_type": "type_e",
        },
        {
            "id": _SAMPLE_IDS["lead"],
            "diagnostic_id": diagnostic_id,
            "sample_number": "AUTH-DEMO-003",
            "location_floor": "2ème étage",
            "location_room": "Salle de bain",
            "location_detail": "Peinture sur boiseries de fenêtre",
            "material_category": "peinture",
            "material_description": "Peinture blanche multicouche",
            "material_state": "intact",
            "pollutant_type": "lead",
            "concentration": 800.0,
            "unit": "mg/kg",
            "threshold_exceeded": False,
            "risk_level": "low",
        },
        {
            "id": _SAMPLE_IDS["hap"],
            "diagnostic_id": diagnostic_id,
            "sample_number": "AUTH-DEMO-004",
            "location_floor": "Sous-sol",
            "location_room": "Parking",
            "location_detail": "Étanchéité de toiture",
            "material_category": "étanchéité",
            "material_description": "Membrane bitumineuse",
            "material_state": "intact",
            "pollutant_type": "hap",
            "concentration": 10.0,
            "unit": "mg/kg",
            "threshold_exceeded": False,
            "risk_level": "low",
        },
        {
            "id": _SAMPLE_IDS["radon"],
            "diagnostic_id": diagnostic_id,
            "sample_number": "AUTH-DEMO-005",
            "location_floor": "Sous-sol",
            "location_room": "Sous-sol",
            "location_detail": "Mesure radon passive 3 mois",
            "material_category": "air",
            "material_description": "Dosimètre radon passif",
            "material_state": "intact",
            "pollutant_type": "radon",
            "concentration": 450.0,
            "unit": "Bq/m3",
            "threshold_exceeded": True,
            "risk_level": "medium",
            "action_required": "Assainissement radon",
            "waste_disposal_type": "type_b",
        },
    ]

    created: dict[str, Sample] = {}
    for spec in sample_specs:
        existing = await db.get(Sample, spec["id"])
        if existing is not None:
            created[spec["pollutant_type"]] = existing
            continue
        sample = Sample(**spec)
        db.add(sample)
        created[spec["pollutant_type"]] = sample

    await db.flush()
    return created


async def _update_diagnostic_metadata(db: AsyncSession, diagnostic: Diagnostic) -> None:
    """Set diagnostic to completed with SUVA/canton notification dates."""
    diagnostic.status = "completed"
    diagnostic.diagnostic_type = "full"
    diagnostic.diagnostic_context = "AvT"
    diagnostic.suva_notification_required = True
    diagnostic.suva_notification_date = date(2025, 11, 15)
    diagnostic.canton_notification_date = date(2025, 11, 20)
    diagnostic.date_inspection = date(2025, 10, 1)
    diagnostic.date_report = date(2025, 10, 15)
    diagnostic.laboratory = "Labo Analytica SA"
    diagnostic.laboratory_report_number = "LA-2025-4567"
    diagnostic.methodology = "VDI 3492 + NIOSH 7400"
    diagnostic.conclusion = "positive"
    diagnostic.summary = (
        "Diagnostic complet 5 polluants. Amiante positif (flocage sous-sol), "
        "PCB positif (joints cuisine), plomb négatif, HAP négatif, radon 450 Bq/m³."
    )
    await db.flush()


async def _ensure_compliance_artefacts(
    db: AsyncSession,
    building_id: uuid.UUID,
    diagnostic_id: uuid.UUID,
) -> list[ComplianceArtefact]:
    """Create SUVA notification and cantonal form artefacts."""
    artefact_specs = [
        {
            "id": _ARTEFACT_IDS["suva"],
            "building_id": building_id,
            "diagnostic_id": diagnostic_id,
            "artefact_type": "suva_notification",
            "status": "submitted",
            "title": "Notification SUVA — Travaux d'amiante",
            "description": "Notification obligatoire SUVA pour travaux de désamiantage (flocage sous-sol).",
            "reference_number": "SUVA-2025-AUTH-001",
            "authority_name": "SUVA",
            "authority_type": "federal",
            "legal_basis": "OTConst Art. 82-86",
            "submitted_at": datetime(2025, 11, 15, tzinfo=UTC),
            "acknowledged_at": datetime(2025, 11, 18, tzinfo=UTC),
        },
        {
            "id": _ARTEFACT_IDS["cantonal"],
            "building_id": building_id,
            "diagnostic_id": diagnostic_id,
            "artefact_type": "cantonal_notification",
            "status": "submitted",
            "title": "Formulaire cantonal — Diagnostic polluants",
            "description": "Formulaire cantonal de notification pour diagnostic de polluants avant travaux.",
            "reference_number": "VD-2025-AUTH-001",
            "authority_name": "Canton de Vaud - DIREN",
            "authority_type": "cantonal",
            "legal_basis": "RLATC Art. 13",
            "submitted_at": datetime(2025, 11, 20, tzinfo=UTC),
        },
    ]

    created: list[ComplianceArtefact] = []
    for spec in artefact_specs:
        existing = await db.get(ComplianceArtefact, spec["id"])
        if existing is not None:
            created.append(existing)
            continue
        artefact = ComplianceArtefact(**spec)
        db.add(artefact)
        created.append(artefact)

    await db.flush()
    return created


async def _ensure_interventions(
    db: AsyncSession,
    building_id: uuid.UUID,
    diagnostic_id: uuid.UUID,
) -> list[Intervention]:
    """Create asbestos removal (completed) and PCB removal (in_progress) interventions."""
    intervention_specs = [
        {
            "id": _INTERVENTION_IDS["asbestos_removal"],
            "building_id": building_id,
            "diagnostic_id": diagnostic_id,
            "intervention_type": "asbestos_removal",
            "title": "Désamiantage complet — Flocage sous-sol",
            "description": (
                "Retrait complet du flocage amianté sur structure métallique au sous-sol. "
                "Confinement zone, extraction sous dépression, mesures libératoires."
            ),
            "status": "completed",
            "date_start": date(2026, 1, 15),
            "date_end": date(2026, 2, 28),
            "contractor_name": "Sanacore Bau GmbH",
            "cost_chf": 85000.0,
            "zones_affected": ["Sous-sol"],
            "materials_used": ["Protection PE", "Aspirateur H14", "Combinaisons jetables"],
        },
        {
            "id": _INTERVENTION_IDS["pcb_removal"],
            "building_id": building_id,
            "diagnostic_id": diagnostic_id,
            "intervention_type": "removal",
            "title": "Retrait joints PCB — Cuisine",
            "description": (
                "Retrait des joints d'étanchéité contenant des PCB en cuisine. Remplacement par joints conformes."
            ),
            "status": "in_progress",
            "date_start": date(2026, 3, 1),
            "contractor_name": "Sanacore Bau GmbH",
            "cost_chf": 12000.0,
            "zones_affected": ["1er étage — Cuisine"],
        },
    ]

    created: list[Intervention] = []
    for spec in intervention_specs:
        existing = await db.get(Intervention, spec["id"])
        if existing is not None:
            created.append(existing)
            continue
        intervention = Intervention(**spec)
        db.add(intervention)
        created.append(intervention)

    await db.flush()
    return created


async def _ensure_documents(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> list[Document]:
    """Create reference documents (no actual files)."""
    doc_specs = [
        {
            "id": _DOCUMENT_IDS["diagnostic_report"],
            "building_id": building_id,
            "file_path": "demo/authority/rapport-diagnostic-polluants.pdf",
            "file_name": "rapport-diagnostic-polluants.pdf",
            "file_size_bytes": 2_500_000,
            "mime_type": "application/pdf",
            "document_type": "diagnostic_report",
            "description": "Rapport de diagnostic complet 5 polluants — Labo Analytica SA",
        },
        {
            "id": _DOCUMENT_IDS["suva_notification"],
            "building_id": building_id,
            "file_path": "demo/authority/notification-suva.pdf",
            "file_name": "notification-suva.pdf",
            "file_size_bytes": 450_000,
            "mime_type": "application/pdf",
            "document_type": "suva_notification",
            "description": "Copie de la notification SUVA pour travaux de désamiantage",
        },
        {
            "id": _DOCUMENT_IDS["waste_elimination_plan"],
            "building_id": building_id,
            "file_path": "demo/authority/plan-elimination-dechets.pdf",
            "file_name": "plan-elimination-dechets.pdf",
            "file_size_bytes": 1_200_000,
            "mime_type": "application/pdf",
            "document_type": "waste_elimination_plan",
            "description": "Plan d'élimination des déchets selon OLED",
        },
    ]

    created: list[Document] = []
    for spec in doc_specs:
        existing = await db.get(Document, spec["id"])
        if existing is not None:
            created.append(existing)
            continue
        doc = Document(**spec)
        db.add(doc)
        created.append(doc)

    await db.flush()
    return created


async def _run_generators(
    db: AsyncSession,
    building_id: uuid.UUID,
    diagnostic_id: uuid.UUID,
    completed_intervention_id: uuid.UUID,
) -> dict:
    """Run all downstream generators in order."""
    summary: dict = {}

    # 1. Generate actions from diagnostic
    try:
        from app.services.action_generator import generate_actions_from_diagnostic

        actions = await generate_actions_from_diagnostic(db, building_id, diagnostic_id)
        summary["actions_generated"] = len(actions)
    except Exception:
        logger.exception("Failed to generate actions")
        summary["actions_generated"] = 0

    # 2. Generate post-works states from completed intervention
    try:
        from app.services.post_works_service import generate_post_works_states

        pws = await generate_post_works_states(db, building_id, completed_intervention_id)
        summary["post_works_states_generated"] = len(pws)
    except Exception:
        logger.exception("Failed to generate post-works states")
        summary["post_works_states_generated"] = 0

    # 3. Evaluate all readiness types
    try:
        from app.services.readiness_reasoner import evaluate_all_readiness

        assessments = await evaluate_all_readiness(db, building_id)
        summary["readiness_assessments"] = len(assessments)
    except Exception:
        logger.exception("Failed to evaluate readiness")
        summary["readiness_assessments"] = 0

    # 4. Calculate trust score
    try:
        from app.services.trust_score_calculator import calculate_trust_score

        trust = await calculate_trust_score(db, building_id, assessed_by="seed_demo_authority")
        summary["trust_score"] = trust.overall_score
    except Exception:
        logger.exception("Failed to calculate trust score")
        summary["trust_score"] = None

    # 5. Generate unknowns
    try:
        from app.services.unknown_generator import generate_unknowns

        unknowns = await generate_unknowns(db, building_id)
        summary["unknowns_generated"] = len(unknowns)
    except Exception:
        logger.exception("Failed to generate unknowns")
        summary["unknowns_generated"] = 0

    # 6. Generate change signals — migrated to canonical detect_signals (2026-03-28, Rail 1)
    # Uses change_tracker_service.detect_signals() which bridges: populates both
    # ChangeSignal (legacy) and BuildingSignal (canonical) tables.
    try:
        from app.services.change_tracker_service import detect_signals

        signals = await detect_signals(db, building_id)
        summary["signals_generated"] = len(signals)
    except Exception:
        logger.exception("Failed to generate change signals")
        summary["signals_generated"] = 0

    # 7. Detect contradictions
    try:
        from app.services.contradiction_detector import detect_contradictions

        contradictions = await detect_contradictions(db, building_id)
        summary["contradictions_detected"] = len(contradictions)
    except Exception:
        logger.exception("Failed to detect contradictions")
        summary["contradictions_detected"] = 0

    return summary


async def seed_authority_demo(db: AsyncSession) -> dict:
    """
    Run the authority-ready demo seed.
    Returns summary of what was created/updated.
    """
    result = await _find_target_building(db)
    if result is None:
        return {"status": "skipped", "reason": "No building with diagnostic found"}

    building, diagnostic = result
    building_id = building.id
    diagnostic_id = diagnostic.id

    logger.info(
        "Authority demo seed: targeting building %s (%s), diagnostic %s",
        building_id,
        building.address,
        diagnostic_id,
    )

    # Step 1: Ensure all 5 pollutant samples
    samples = await _ensure_samples(db, diagnostic_id)

    # Step 2: Update diagnostic metadata
    await _update_diagnostic_metadata(db, diagnostic)

    # Step 3: Create compliance artefacts
    artefacts = await _ensure_compliance_artefacts(db, building_id, diagnostic_id)

    # Step 4: Create interventions
    interventions = await _ensure_interventions(db, building_id, diagnostic_id)

    # Step 5: Create documents
    documents = await _ensure_documents(db, building_id)

    # Commit base data before running generators
    await db.commit()

    # Step 6: Run all downstream generators
    completed_intervention_id = _INTERVENTION_IDS["asbestos_removal"]
    generator_summary = await _run_generators(db, building_id, diagnostic_id, completed_intervention_id)

    await db.commit()

    return {
        "status": "completed",
        "building_id": str(building_id),
        "building_address": building.address,
        "diagnostic_id": str(diagnostic_id),
        "samples_count": len(samples),
        "artefacts_count": len(artefacts),
        "interventions_count": len(interventions),
        "documents_count": len(documents),
        **generator_summary,
    }


if __name__ == "__main__":
    import asyncio

    from app.database import AsyncSessionLocal

    async def main():
        async with AsyncSessionLocal() as db:
            result = await seed_authority_demo(db)
            print(result)

    asyncio.run(main())
