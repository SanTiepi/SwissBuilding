"""
BatiConnect - Prospect Demo Seed

Narrative: "You thought the dossier was complete because the PDFs exist.
In reality it's not ready."

Takes ONE existing VD building and stages a deceptively "documented" dossier:
- 3 diagnostics: one EXPIRED (>3 years), one with SCOPE GAP (no basement), one current
- 4 documents: PDFs that look complete on the surface
- 1 contradiction: two diagnostics disagree on asbestos in wall coating
- 1 missing mandatory piece: no waste disposal plan (required for VD AvT)
- 1 planned intervention: renovation that triggers the readiness checks

Then runs all generators so the UI reveals:
  Passport looks OK -> completeness reveals holes -> readiness says "not ready"
  -> actions show exactly what to fix

Idempotent: can be run multiple times safely.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SOURCE_DATASET_VAUD_PUBLIC
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# Stable UUIDs for idempotency
_NS = uuid.UUID("a105a3c7-de40-7890-abcd-ef1234567890")
_DIAG_IDS = {
    "expired": uuid.uuid5(_NS, "prospect-diag-expired"),
    "partial_scope": uuid.uuid5(_NS, "prospect-diag-partial-scope"),
    "recent_pcb": uuid.uuid5(_NS, "prospect-diag-recent-pcb"),
}
_SAMPLE_IDS = {
    "expired_absence": uuid.uuid5(_NS, "prospect-sample-expired-absence"),
    "partial_presence": uuid.uuid5(_NS, "prospect-sample-partial-presence"),
    "pcb_joint": uuid.uuid5(_NS, "prospect-sample-pcb-joint"),
}
_DOC_IDS = {
    "diag_report_2022": uuid.uuid5(_NS, "prospect-doc-diag-report-2022"),
    "diag_report_2025": uuid.uuid5(_NS, "prospect-doc-diag-report-2025"),
    "pcb_report": uuid.uuid5(_NS, "prospect-doc-pcb-report"),
    "plan_travaux": uuid.uuid5(_NS, "prospect-doc-plan-travaux"),
}
_INTERVENTION_ID = uuid.uuid5(_NS, "prospect-intervention-renovation")


async def _find_vd_building(db: AsyncSession) -> Building | None:
    """Find the first VD building from the public dataset."""
    stmt = (
        select(Building)
        .where(Building.source_dataset == SOURCE_DATASET_VAUD_PUBLIC)
        .order_by(Building.created_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _ensure_diagnostics(db: AsyncSession, building_id: uuid.UUID) -> None:
    """Create 3 diagnostics: expired, partial-scope, and recent PCB."""
    specs = [
        # 1. EXPIRED: completed in 2022, >3 years old = no longer valid
        {
            "id": _DIAG_IDS["expired"],
            "building_id": building_id,
            "diagnostic_type": "asbestos",
            "diagnostic_context": "AvT",
            "status": "completed",
            "conclusion": "absence",
            "date_inspection": date(2022, 3, 15),
            "date_report": date(2022, 4, 1),
            "laboratory": "Labo Analytica SA",
            "laboratory_report_number": "LA-2022-1234",
            "methodology": "VDI 3492",
            "summary": (
                "Diagnostic amiante avant travaux. Aucune fibre detectee "
                "dans les revetements muraux du 1er et 2eme etage."
            ),
        },
        # 2. PARTIAL SCOPE: recent but covers only floors 1-3 (NOT basement)
        {
            "id": _DIAG_IDS["partial_scope"],
            "building_id": building_id,
            "diagnostic_type": "asbestos",
            "diagnostic_context": "AvT",
            "status": "completed",
            "conclusion": "positive",
            "date_inspection": date(2025, 9, 10),
            "date_report": date(2025, 9, 25),
            "laboratory": "EnviroLab Suisse",
            "laboratory_report_number": "ELS-2025-5678",
            "methodology": "VDI 3492 + NIOSH 7400",
            "summary": (
                "Diagnostic amiante etages 1-3. Presence confirmee dans "
                "revetement mural (crepi) au 2eme etage. Sous-sol NON couvert."
            ),
            "suva_notification_required": True,
            "suva_notification_date": date(2025, 10, 1),
        },
        # 3. Recent PCB diagnostic (clean, no issue here)
        {
            "id": _DIAG_IDS["recent_pcb"],
            "building_id": building_id,
            "diagnostic_type": "pcb",
            "diagnostic_context": "AvT",
            "status": "completed",
            "conclusion": "positive",
            "date_inspection": date(2025, 9, 12),
            "date_report": date(2025, 9, 28),
            "laboratory": "EnviroLab Suisse",
            "laboratory_report_number": "ELS-2025-5679",
            "methodology": "EPA 8082A",
            "summary": "Diagnostic PCB. Joints de facade positifs (85 mg/kg > seuil 50 mg/kg).",
        },
    ]
    for spec in specs:
        if await db.get(Diagnostic, spec["id"]) is None:
            db.add(Diagnostic(**spec))
    await db.flush()


async def _ensure_samples(db: AsyncSession) -> None:
    """Create samples that set up the contradiction.

    Contradiction: the expired diagnostic says "absence" for wall coating,
    but the recent partial-scope says "presence" for the same material.
    """
    specs = [
        # Expired diag sample: says NO asbestos in wall coating
        {
            "id": _SAMPLE_IDS["expired_absence"],
            "diagnostic_id": _DIAG_IDS["expired"],
            "sample_number": "PROS-001",
            "location_floor": "2eme etage",
            "location_room": "Couloir",
            "location_detail": "Revetement mural (crepi)",
            "material_category": "revetement_mural",
            "material_description": "Crepi interieur blanc",
            "material_state": "intact",
            "pollutant_type": "asbestos",
            "concentration": 0.0,
            "unit": "%",
            "threshold_exceeded": False,
            "risk_level": "low",
        },
        # Recent diag sample: says YES asbestos in same material type
        {
            "id": _SAMPLE_IDS["partial_presence"],
            "diagnostic_id": _DIAG_IDS["partial_scope"],
            "sample_number": "PROS-002",
            "location_floor": "2eme etage",
            "location_room": "Couloir",
            "location_detail": "Revetement mural (crepi)",
            "material_category": "revetement_mural",
            "material_description": "Crepi interieur blanc",
            "material_state": "degraded",
            "pollutant_type": "asbestos",
            "pollutant_subtype": "chrysotile",
            "concentration": 8.0,
            "unit": "%",
            "threshold_exceeded": True,
            "risk_level": "high",
            "cfst_work_category": "major",
            "action_required": "Desamiantage",
            "waste_disposal_type": "special",
        },
        # PCB sample (straightforward positive)
        {
            "id": _SAMPLE_IDS["pcb_joint"],
            "diagnostic_id": _DIAG_IDS["recent_pcb"],
            "sample_number": "PROS-003",
            "location_floor": "Facade",
            "location_room": "Facade est",
            "location_detail": "Joint d'etancheite entre panneaux",
            "material_category": "joint",
            "material_description": "Mastic d'etancheite gris",
            "material_state": "degraded",
            "pollutant_type": "pcb",
            "concentration": 85.0,
            "unit": "mg/kg",
            "threshold_exceeded": True,
            "risk_level": "medium",
            "action_required": "Retrait joints PCB",
            "waste_disposal_type": "type_e",
        },
    ]
    for spec in specs:
        if await db.get(Sample, spec["id"]) is None:
            db.add(Sample(**spec))
    await db.flush()


async def _ensure_documents(db: AsyncSession, building_id: uuid.UUID) -> None:
    """Create 4 documents that make the dossier LOOK complete.

    Notably MISSING: waste disposal plan (plan de gestion des dechets)
    which is mandatory for VD AvT works.
    """
    specs = [
        {
            "id": _DOC_IDS["diag_report_2022"],
            "building_id": building_id,
            "file_path": "demo/prospect/rapport-amiante-2022.pdf",
            "file_name": "rapport-amiante-2022.pdf",
            "file_size_bytes": 1_800_000,
            "mime_type": "application/pdf",
            "document_type": "diagnostic_report",
            "description": "Rapport diagnostic amiante 2022 (EXPIRE - plus de 3 ans)",
        },
        {
            "id": _DOC_IDS["diag_report_2025"],
            "building_id": building_id,
            "file_path": "demo/prospect/rapport-amiante-2025.pdf",
            "file_name": "rapport-amiante-2025.pdf",
            "file_size_bytes": 2_200_000,
            "mime_type": "application/pdf",
            "document_type": "diagnostic_report",
            "description": "Rapport diagnostic amiante 2025 (etages 1-3, sous-sol non couvert)",
        },
        {
            "id": _DOC_IDS["pcb_report"],
            "building_id": building_id,
            "file_path": "demo/prospect/rapport-pcb-2025.pdf",
            "file_name": "rapport-pcb-2025.pdf",
            "file_size_bytes": 1_500_000,
            "mime_type": "application/pdf",
            "document_type": "diagnostic_report",
            "description": "Rapport diagnostic PCB facade 2025",
        },
        {
            "id": _DOC_IDS["plan_travaux"],
            "building_id": building_id,
            "file_path": "demo/prospect/plan-travaux-renovation.pdf",
            "file_name": "plan-travaux-renovation.pdf",
            "file_size_bytes": 3_100_000,
            "mime_type": "application/pdf",
            "document_type": "project_plan",
            "description": "Plan de travaux renovation complete (inclut sous-sol)",
        },
        # NOTE: No waste_elimination_plan -- this is the missing mandatory piece
    ]
    for spec in specs:
        if await db.get(Document, spec["id"]) is None:
            db.add(Document(**spec))
    await db.flush()


async def _ensure_intervention(db: AsyncSession, building_id: uuid.UUID) -> None:
    """Create a planned renovation that includes the basement.

    This is the trigger: works are planned for the whole building including
    basement, but the asbestos diagnostic does NOT cover the basement.
    """
    if await db.get(Intervention, _INTERVENTION_ID) is not None:
        return
    db.add(
        Intervention(
            id=_INTERVENTION_ID,
            building_id=building_id,
            intervention_type="renovation",
            title="Renovation complete — facade + interieur + sous-sol",
            description=(
                "Renovation energetique complete incluant isolation facade, "
                "remplacement fenetres, refection interieure et assainissement sous-sol. "
                "Travaux prevus Q3 2026."
            ),
            status="planned",
            date_start=date(2026, 7, 1),
            zones_affected=["Facade", "1er etage", "2eme etage", "3eme etage", "Sous-sol"],
            cost_chf=450_000.0,
            notes="Le sous-sol n'est PAS couvert par le diagnostic amiante actuel.",
        )
    )
    await db.flush()


async def _run_generators(db: AsyncSession, building_id: uuid.UUID) -> dict:
    """Run downstream generators to reveal the hidden problems."""
    summary: dict = {}

    # 1. Actions from each diagnostic
    try:
        from app.services.action_generator import generate_actions_from_diagnostic

        total = 0
        for diag_id in _DIAG_IDS.values():
            actions = await generate_actions_from_diagnostic(db, building_id, diag_id)
            total += len(actions)
        summary["actions_generated"] = total
    except Exception:
        logger.exception("Failed to generate actions")
        summary["actions_generated"] = 0

    # 2. Unknowns (will flag scope gap + missing waste plan)
    try:
        from app.services.unknown_generator import generate_unknowns

        unknowns = await generate_unknowns(db, building_id)
        summary["unknowns_generated"] = len(unknowns)
    except Exception:
        logger.exception("Failed to generate unknowns")
        summary["unknowns_generated"] = 0

    # 3. Readiness evaluation (will say "not ready")
    try:
        from app.services.readiness_reasoner import evaluate_all_readiness

        assessments = await evaluate_all_readiness(db, building_id)
        summary["readiness_assessments"] = len(assessments)
    except Exception:
        logger.exception("Failed to evaluate readiness")
        summary["readiness_assessments"] = 0

    # 4. Readiness actions (converts blocked checks into actionable items)
    try:
        from app.services.readiness_action_generator import generate_readiness_actions

        ra = await generate_readiness_actions(db, building_id)
        summary["readiness_actions"] = len(ra)
    except Exception:
        logger.exception("Failed to generate readiness actions")
        summary["readiness_actions"] = 0

    # 5. Contradiction detection (will find the asbestos disagreement)
    try:
        from app.services.contradiction_detector import detect_contradictions

        contradictions = await detect_contradictions(db, building_id)
        summary["contradictions_detected"] = len(contradictions)
    except Exception:
        logger.exception("Failed to detect contradictions")
        summary["contradictions_detected"] = 0

    # 6. Trust score
    try:
        from app.services.trust_score_calculator import calculate_trust_score

        trust = await calculate_trust_score(db, building_id, assessed_by="seed_demo_prospect")
        summary["trust_score"] = trust.overall_score
    except Exception:
        logger.exception("Failed to calculate trust score")
        summary["trust_score"] = None

    # 7. Completeness evaluation
    try:
        from app.services.completeness_engine import evaluate_completeness

        completeness = await evaluate_completeness(db, building_id)
        summary["completeness_score"] = completeness.overall_score
    except Exception:
        logger.exception("Failed to evaluate completeness")
        summary["completeness_score"] = None

    return summary


async def seed_prospect_demo(db: AsyncSession) -> dict:
    """
    Seed the prospect demo scenario.
    Returns summary of what was created and generator results.
    """
    building = await _find_vd_building(db)
    if building is None:
        return {"status": "skipped", "reason": "No VD public building found. Run Vaud import first."}

    building_id = building.id
    logger.info(
        "Prospect demo seed: targeting building %s (%s)",
        building_id,
        building.address,
    )

    # Stage the "looks complete" dossier with hidden problems
    await _ensure_diagnostics(db, building_id)
    await _ensure_samples(db)
    await _ensure_documents(db, building_id)
    await _ensure_intervention(db, building_id)
    await db.commit()

    # Run generators to surface the problems
    generator_summary = await _run_generators(db, building_id)
    await db.commit()

    return {
        "status": "completed",
        "building_id": str(building_id),
        "building_address": building.address,
        "narrative": "Dossier looks documented (4 PDFs, 3 diagnostics) but is NOT ready",
        "hidden_problems": [
            "Diagnostic amiante 2022 expire (>3 ans)",
            "Diagnostic amiante 2025 ne couvre pas le sous-sol (travaux prevus au sous-sol)",
            "Contradiction: absence vs presence amiante dans revetement mural 2eme etage",
            "Plan de gestion des dechets manquant (obligatoire VD AvT)",
        ],
        **generator_summary,
    }


if __name__ == "__main__":
    import asyncio

    from app.database import AsyncSessionLocal

    async def main():
        async with AsyncSessionLocal() as db:
            result = await seed_prospect_demo(db)
            for k, v in result.items():
                print(f"  {k}: {v}")

    asyncio.run(main())
