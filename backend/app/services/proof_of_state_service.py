"""
SwissBuildingOS - Proof of State Service

Generates a comprehensive, exportable building state snapshot suitable for
insurance, bank, tribunal, or sale contexts. Machine-readable JSON with
integrity verification via SHA-256 hash.

Unlike transfer_package_service (which bundles summaries for handoff), this
service produces a fully self-contained proof document with every data point
needed to independently verify the building's state at a point in time.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue

logger = logging.getLogger(__name__)

PROOF_OF_STATE_VERSION = "1.0"


def _compute_integrity_hash(content: dict) -> str:
    """Compute SHA-256 hash of the content dict (excluding integrity field)."""
    serializable = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(serializable.encode("utf-8")).hexdigest()


def _anonymize_sample(sample: Sample) -> dict:
    """Extract sample data without personal information."""
    return {
        "id": str(sample.id),
        "diagnostic_id": str(sample.diagnostic_id),
        "sample_number": sample.sample_number,
        "location_floor": sample.location_floor,
        "location_room": sample.location_room,
        "location_detail": sample.location_detail,
        "material_category": sample.material_category,
        "material_description": sample.material_description,
        "material_state": sample.material_state,
        "pollutant_type": sample.pollutant_type,
        "concentration": sample.concentration,
        "unit": sample.unit,
        "risk_level": sample.risk_level,
        "threshold_exceeded": sample.threshold_exceeded,
        "action_required": sample.action_required,
        "created_at": sample.created_at.isoformat() if sample.created_at else None,
    }


async def generate_proof_of_state(
    db: AsyncSession,
    building_id: UUID,
    requested_by_id: UUID,
    format: str = "json",
) -> dict | None:
    """Generate a comprehensive proof-of-state export for a building.

    Returns None if the building does not exist.
    Returns the full dict with all sections and an integrity hash.
    """
    # ── 0. Fetch building ─────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    export_id = uuid4()
    generated_at = datetime.now(UTC)

    # ── Metadata ──────────────────────────────────────────────────
    metadata = {
        "export_id": str(export_id),
        "generated_at": generated_at.isoformat(),
        "generated_by": str(requested_by_id),
        "format_version": PROOF_OF_STATE_VERSION,
        "building_id": str(building_id),
    }

    # ── Building basic info ───────────────────────────────────────
    building_info = {
        "address": building.address,
        "city": building.city,
        "postal_code": building.postal_code,
        "construction_year": building.construction_year,
        "egid": building.egid,
        "canton": building.canton,
        "building_type": building.building_type,
    }

    # ── Evidence score ────────────────────────────────────────────
    evidence_score: dict | None = None
    try:
        from app.services.evidence_score_service import compute_evidence_score

        evidence_score = await compute_evidence_score(db, building_id)
    except Exception as e:
        logger.warning("Failed to compute evidence score for building %s: %s", building_id, e)

    # ── Passport ──────────────────────────────────────────────────
    passport: dict | None = None
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
    except Exception as e:
        logger.warning("Failed to get passport for building %s: %s", building_id, e)

    # ── Completeness ──────────────────────────────────────────────
    completeness: dict | None = None
    try:
        from app.services.completeness_engine import evaluate_completeness

        comp_result = await evaluate_completeness(db, building_id)
        completeness = {
            "overall_score": comp_result.overall_score,
            "checks_passed": sum(1 for c in comp_result.checks if c.status == "complete"),
            "checks_failed": sum(1 for c in comp_result.checks if c.status == "missing"),
            "missing_items": comp_result.missing_items,
            "ready_to_proceed": comp_result.ready_to_proceed,
        }
    except Exception as e:
        logger.warning("Failed to evaluate completeness for building %s: %s", building_id, e)

    # ── Trust score ───────────────────────────────────────────────
    trust: dict | None = None
    try:
        from app.services.trust_score_calculator import compute_building_trust_score

        trust = await compute_building_trust_score(db, building_id)
    except Exception as e:
        logger.warning("Failed to compute trust score for building %s: %s", building_id, e)

    # ── Diagnostics (no personal data) ────────────────────────────
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics_list = list(diag_result.scalars().all())
    diagnostics = [
        {
            "id": str(d.id),
            "diagnostic_type": d.diagnostic_type,
            "status": d.status,
            "date_inspection": d.date_inspection.isoformat() if d.date_inspection else None,
        }
        for d in diagnostics_list
    ]

    # ── Samples (anonymized) ──────────────────────────────────────
    samples: list[dict] = []
    if diagnostics_list:
        diag_ids = [d.id for d in diagnostics_list]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = [_anonymize_sample(s) for s in sample_result.scalars().all()]

    # ── Documents (hash only, no content) ─────────────────────────
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = [
        {
            "id": str(doc.id),
            "document_type": doc.document_type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "content_hash": doc.content_hash,
        }
        for doc in doc_result.scalars().all()
    ]

    # ── Actions ───────────────────────────────────────────────────
    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = [
        {
            "id": str(a.id),
            "title": a.title,
            "status": a.status,
            "priority": a.priority,
            "source_type": a.source_type,
        }
        for a in action_result.scalars().all()
    ]

    # ── Timeline (last 100 events) ────────────────────────────────
    timeline_events: list[dict] = []
    try:
        from app.services.timeline_service import get_building_timeline

        entries, _total = await get_building_timeline(db, building_id, page=1, size=100)
        timeline_events = [
            {
                "id": e.id,
                "date": e.date.isoformat() if e.date else None,
                "event_type": e.event_type,
                "title": e.title,
            }
            for e in entries
        ]
    except Exception as e:
        logger.warning("Failed to get timeline for building %s: %s", building_id, e)

    # ── Readiness (4 evaluations) ─────────────────────────────────
    readiness: dict | None = None
    if passport and "readiness" in passport:
        readiness = passport["readiness"]
    else:
        try:
            from app.services.passport_service import get_passport_summary

            passport_data = await get_passport_summary(db, building_id)
            if passport_data:
                readiness = passport_data.get("readiness")
        except Exception as e:
            logger.warning("Failed to get readiness for building %s: %s", building_id, e)

    # ── Unknowns ──────────────────────────────────────────────────
    unknown_result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
    )
    open_unknowns = list(unknown_result.scalars().all())
    unknowns = [
        {
            "id": str(u.id),
            "unknown_type": u.unknown_type,
            "description": u.description,
            "blocks_readiness": u.blocks_readiness,
        }
        for u in open_unknowns
    ]

    # ── Contradictions ────────────────────────────────────────────
    contradictions: dict | None = None
    try:
        from app.services.contradiction_detector import get_contradiction_summary

        contradictions = await get_contradiction_summary(db, building_id)
    except Exception as e:
        logger.warning("Failed to get contradictions for building %s: %s", building_id, e)

    # ── Assemble content (without integrity hash) ─────────────────
    content = {
        "metadata": metadata,
        "building": building_info,
        "evidence_score": evidence_score,
        "passport": passport,
        "completeness": completeness,
        "trust": trust,
        "diagnostics": diagnostics,
        "samples": samples,
        "documents": documents,
        "actions": actions,
        "timeline": timeline_events,
        "readiness": readiness,
        "unknowns": unknowns,
        "contradictions": contradictions,
    }

    # ── Compute integrity hash BEFORE adding it ───────────────────
    integrity_hash = _compute_integrity_hash(content)
    content["integrity"] = {
        "algorithm": "sha256",
        "hash": integrity_hash,
    }

    return content


async def generate_proof_of_state_summary(
    db: AsyncSession,
    building_id: UUID,
    requested_by_id: UUID,
) -> dict | None:
    """Generate a compact proof-of-state summary.

    Contains only: metadata + evidence_score + passport + readiness + integrity.
    Suitable for quick sharing without full data export.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    export_id = uuid4()
    generated_at = datetime.now(UTC)

    metadata = {
        "export_id": str(export_id),
        "generated_at": generated_at.isoformat(),
        "generated_by": str(requested_by_id),
        "format_version": PROOF_OF_STATE_VERSION,
        "building_id": str(building_id),
        "summary_only": True,
    }

    # ── Evidence score ────────────────────────────────────────────
    evidence_score: dict | None = None
    try:
        from app.services.evidence_score_service import compute_evidence_score

        evidence_score = await compute_evidence_score(db, building_id)
    except Exception as e:
        logger.warning("Failed to compute evidence score for building %s: %s", building_id, e)

    # ── Passport ──────────────────────────────────────────────────
    passport: dict | None = None
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
    except Exception as e:
        logger.warning("Failed to get passport for building %s: %s", building_id, e)

    # ── Readiness ─────────────────────────────────────────────────
    readiness: dict | None = None
    if passport and "readiness" in passport:
        readiness = passport["readiness"]

    content = {
        "metadata": metadata,
        "evidence_score": evidence_score,
        "passport": passport,
        "readiness": readiness,
    }

    integrity_hash = _compute_integrity_hash(content)
    content["integrity"] = {
        "algorithm": "sha256",
        "hash": integrity_hash,
    }

    return content
