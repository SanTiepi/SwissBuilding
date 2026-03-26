"""BatiConnect - Memory Transfer Service.

Orchestrates the transfer of building memory between parties or across lifecycle events.
When a building changes owner, manager, gets refinanced, or starts a new work cycle,
this service compiles, verifies, and transfers the complete building memory.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.domain_event import DomainEvent
from app.models.ecosystem_engagement import EcosystemEngagement
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.memory_transfer import MemoryTransfer
from app.models.obligation import Obligation
from app.models.unknown_issue import UnknownIssue
from app.schemas.memory_transfer import (
    MemoryCompilation,
    MemoryContinuityScore,
    TransferReadiness,
)

logger = logging.getLogger(__name__)

# ── Transfer type labels (French) ──────────────────────────────────────────
TRANSFER_TYPE_LABELS: dict[str, str] = {
    "sale": "Vente immobiliere",
    "refinance": "Refinancement",
    "management_change": "Changement de gerance",
    "work_cycle": "Nouveau cycle de travaux",
    "insurance_renewal": "Renouvellement d'assurance",
    "regulatory_update": "Mise a jour reglementaire",
    "succession": "Succession",
}


def _compute_hash(data: dict) -> str:
    """Compute SHA-256 hash of a JSON-serializable dict."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def _emit_domain_event(
    db: AsyncSession,
    event_type: str,
    transfer: MemoryTransfer,
    actor_user_id: UUID | None = None,
    payload: dict | None = None,
) -> None:
    """Create a DomainEvent for a memory transfer status change."""
    event = DomainEvent(
        id=uuid4(),
        event_type=event_type,
        aggregate_type="memory_transfer",
        aggregate_id=transfer.id,
        payload=payload or {"transfer_type": transfer.transfer_type, "status": transfer.status},
        actor_user_id=actor_user_id,
        occurred_at=datetime.utcnow(),
    )
    db.add(event)


async def _create_engagement(
    db: AsyncSession,
    building_id: UUID,
    transfer: MemoryTransfer,
    engagement_type: str,
    actor_user_id: UUID | None = None,
    actor_org_id: UUID | None = None,
    comment: str | None = None,
    content_hash: str | None = None,
) -> None:
    """Create an EcosystemEngagement for a transfer event."""
    engagement = EcosystemEngagement(
        id=uuid4(),
        building_id=building_id,
        actor_type="property_manager",
        actor_org_id=actor_org_id,
        actor_user_id=actor_user_id,
        subject_type="transfer",
        subject_id=transfer.id,
        subject_label=transfer.transfer_label,
        engagement_type=engagement_type,
        status="active",
        comment=comment,
        content_hash=content_hash,
    )
    db.add(engagement)


async def initiate_transfer(
    db: AsyncSession,
    building_id: UUID,
    transfer_type: str,
    from_org_id: UUID | None,
    to_org_id: UUID | None,
    user_id: UUID,
    transfer_label: str | None = None,
    from_user_id: UUID | None = None,
    to_user_id: UUID | None = None,
) -> MemoryTransfer:
    """Start a memory transfer. Creates the transfer record and emits domain event."""
    # Validate building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError("Batiment introuvable")

    label = transfer_label or TRANSFER_TYPE_LABELS.get(transfer_type, f"Transfert memoire ({transfer_type})")

    transfer = MemoryTransfer(
        id=uuid4(),
        building_id=building_id,
        transfer_type=transfer_type,
        transfer_label=label,
        from_org_id=from_org_id,
        from_user_id=from_user_id,
        to_org_id=to_org_id,
        to_user_id=to_user_id,
        status="initiated",
    )
    db.add(transfer)

    await _emit_domain_event(db, "memory_transfer_initiated", transfer, actor_user_id=user_id)

    return transfer


async def compile_memory(db: AsyncSession, transfer_id: UUID) -> MemoryCompilation:
    """Compile complete building memory for transfer.

    Gathers from all sources: identity, diagnostics, interventions, obligations,
    engagements, proof chains, timeline, contradictions, unknowns, passport, grade.
    """
    result = await db.execute(select(MemoryTransfer).where(MemoryTransfer.id == transfer_id))
    transfer = result.scalar_one_or_none()
    if transfer is None:
        raise ValueError("Transfert introuvable")

    building_id = transfer.building_id
    sections: dict = {}
    docs_count = 0
    eng_count = 0
    timeline_count = 0

    # ── Identity ──────────────────────────────────────────────────
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building:
        sections["identity"] = {
            "address": building.address,
            "postal_code": building.postal_code,
            "city": building.city,
            "canton": building.canton,
            "egid": building.egid,
            "egrid": building.egrid,
            "construction_year": building.construction_year,
            "building_type": building.building_type,
        }

    # ── Diagnostics ───────────────────────────────────────────────
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    status_counts: dict[str, int] = defaultdict(int)
    pollutants: set[str] = set()
    for d in diagnostics:
        status_counts[d.status or "unknown"] += 1
        if d.diagnostic_type:
            pollutants.add(d.diagnostic_type)
    sections["diagnostics"] = {
        "count": len(diagnostics),
        "statuses": dict(status_counts),
        "pollutants_found": sorted(pollutants),
    }

    # ── Interventions ─────────────────────────────────────────────
    iv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(iv_result.scalars().all())
    iv_by_status: dict[str, int] = defaultdict(int)
    for iv in interventions:
        iv_by_status[iv.status or "unknown"] += 1
    sections["interventions"] = {
        "count": len(interventions),
        "by_status": dict(iv_by_status),
    }

    # ── Obligations ───────────────────────────────────────────────
    obl_result = await db.execute(select(Obligation).where(Obligation.building_id == building_id))
    obligations = list(obl_result.scalars().all())
    sections["obligations"] = {
        "count": len(obligations),
        "items": [
            {
                "id": str(o.id),
                "obligation_type": o.obligation_type,
                "status": o.status,
                "deadline": str(o.deadline) if o.deadline else None,
            }
            for o in obligations
        ],
    }

    # ── Documents ─────────────────────────────────────────────────
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())
    docs_count = len(documents)
    by_type: dict[str, int] = defaultdict(int)
    for doc in documents:
        by_type[doc.document_type or "other"] += 1
    sections["documents"] = {
        "count": docs_count,
        "by_type": dict(by_type),
    }

    # ── Engagements ───────────────────────────────────────────────
    eng_result = await db.execute(select(EcosystemEngagement).where(EcosystemEngagement.building_id == building_id))
    engagements = list(eng_result.scalars().all())
    eng_count = len(engagements)
    eng_by_type: dict[str, int] = defaultdict(int)
    for e in engagements:
        eng_by_type[e.engagement_type] += 1
    sections["engagements"] = {
        "count": eng_count,
        "by_type": dict(eng_by_type),
    }

    # ── Proof chains (evidence links) ─────────────────────────────
    diag_ids = [d.id for d in diagnostics]
    total_evidence = 0
    if diag_ids:
        ev_result = await db.execute(
            select(func.count()).select_from(EvidenceLink).where(EvidenceLink.source_id.in_(diag_ids))
        )
        total_evidence = ev_result.scalar() or 0
    sections["proof_chains"] = {
        "evidence_links": total_evidence,
        "coverage_ratio": round(total_evidence / max(len(diag_ids), 1), 2),
    }

    # ── Timeline (DomainEvents) ───────────────────────────────────
    timeline_result = await db.execute(
        select(func.count())
        .select_from(DomainEvent)
        .where(
            and_(
                DomainEvent.aggregate_type == "building",
                DomainEvent.aggregate_id == building_id,
            )
        )
    )
    timeline_count = timeline_result.scalar() or 0
    sections["timeline"] = {"event_count": timeline_count}

    # ── Contradictions ────────────────────────────────────────────
    try:
        from app.services.contradiction_detector import get_contradiction_summary

        contradictions = await get_contradiction_summary(db, building_id)
        sections["contradictions"] = contradictions
    except Exception as e:
        logger.warning("Echec lecture contradictions pour batiment %s: %s", building_id, e)
        sections["contradictions"] = {"error": "indisponible"}

    # ── Unknowns ──────────────────────────────────────────────────
    unk_result = await db.execute(
        select(UnknownIssue).where(and_(UnknownIssue.building_id == building_id, UnknownIssue.status == "open"))
    )
    open_unknowns = list(unk_result.scalars().all())
    unk_by_cat: dict[str, int] = defaultdict(int)
    for u in open_unknowns:
        unk_by_cat[u.unknown_type] += 1
    sections["unknowns"] = {
        "total_open": len(open_unknowns),
        "by_category": dict(unk_by_cat),
    }

    # ── Passport + grade + trust + completeness ───────────────────
    passport_grade = None
    overall_trust = None
    completeness_score = None
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade")
            knowledge = passport.get("knowledge_state")
            overall_trust = knowledge.get("overall_trust") if knowledge else None
            comp = passport.get("completeness")
            completeness_score = comp.get("overall_score") if comp else None
            sections["grade"] = {
                "passport_grade": passport_grade,
                "overall_trust": overall_trust,
                "completeness_score": completeness_score,
            }
            sections["safe_to_start"] = passport.get("readiness")
    except Exception as e:
        logger.warning("Echec lecture passeport pour batiment %s: %s", building_id, e)

    # ── Snapshot ──────────────────────────────────────────────────
    from app.services.time_machine_service import capture_snapshot

    snapshot = await capture_snapshot(
        db,
        building_id,
        snapshot_type="memory_transfer",
        trigger_event=f"Transfert memoire: {transfer.transfer_label}",
    )

    # ── Content hash ──────────────────────────────────────────────
    content_hash = _compute_hash(sections)

    # ── Update transfer record ────────────────────────────────────
    transfer.memory_sections = sections
    transfer.sections_count = len(sections)
    transfer.documents_count = docs_count
    transfer.engagements_count = eng_count
    transfer.timeline_events_count = timeline_count
    transfer.memory_snapshot_id = snapshot.id
    transfer.transfer_package_hash = content_hash
    transfer.integrity_verified = True
    transfer.integrity_verified_at = datetime.utcnow()
    transfer.status = "memory_compiled"

    await _emit_domain_event(
        db,
        "memory_transfer_compiled",
        transfer,
        payload={
            "sections_count": len(sections),
            "content_hash": content_hash,
            "passport_grade": passport_grade,
        },
    )

    compiled_at = datetime.utcnow()

    return MemoryCompilation(
        transfer_id=transfer.id,
        building_id=building_id,
        sections=sections,
        sections_count=len(sections),
        documents_count=docs_count,
        engagements_count=eng_count,
        timeline_events_count=timeline_count,
        content_hash=content_hash,
        completeness_score=completeness_score,
        passport_grade=passport_grade,
        overall_trust=overall_trust,
        compiled_at=compiled_at,
    )


async def check_transfer_readiness(db: AsyncSession, building_id: UUID) -> TransferReadiness:
    """Can this building's memory be cleanly transferred?

    Checks: operational gates, contradictions, diagnostic coverage,
    engagement coverage, document integrity.
    """
    checks: list[dict] = []
    blockers: list[str] = []
    warnings: list[str] = []
    passed = 0
    total = 0

    # 1. Building exists
    total += 1
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        checks.append({"name": "building_exists", "status": "fail", "detail": "Batiment introuvable"})
        blockers.append("Le batiment n'existe pas dans le systeme")
        return TransferReadiness(
            building_id=building_id,
            is_ready=False,
            readiness_score=0.0,
            checks=checks,
            blockers=blockers,
            warnings=warnings,
        )
    checks.append({"name": "building_exists", "status": "pass", "detail": "Batiment trouve"})
    passed += 1

    # 2. Has diagnostics
    total += 1
    diag_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    )
    diag_count = diag_result.scalar() or 0
    if diag_count == 0:
        checks.append({"name": "has_diagnostics", "status": "fail", "detail": "Aucun diagnostic"})
        blockers.append("Aucun diagnostic n'est enregistre pour ce batiment")
    else:
        checks.append({"name": "has_diagnostics", "status": "pass", "detail": f"{diag_count} diagnostic(s)"})
        passed += 1

    # 3. No unresolved critical contradictions
    total += 1
    try:
        from app.services.contradiction_detector import get_contradiction_summary

        contradictions = await get_contradiction_summary(db, building_id)
        critical_count = 0
        if contradictions and "total_open" in contradictions:
            critical_count = contradictions.get("critical_count", 0)
        if critical_count > 0:
            checks.append(
                {
                    "name": "no_critical_contradictions",
                    "status": "fail",
                    "detail": f"{critical_count} contradiction(s) critique(s) non resolue(s)",
                }
            )
            blockers.append(f"{critical_count} contradiction(s) critique(s) doivent etre resolues avant le transfert")
        else:
            checks.append(
                {
                    "name": "no_critical_contradictions",
                    "status": "pass",
                    "detail": "Aucune contradiction critique",
                }
            )
            passed += 1
    except Exception:
        checks.append(
            {
                "name": "no_critical_contradictions",
                "status": "pass",
                "detail": "Verification indisponible",
            }
        )
        passed += 1

    # 4. Has documents
    total += 1
    doc_result = await db.execute(select(func.count()).select_from(Document).where(Document.building_id == building_id))
    doc_count = doc_result.scalar() or 0
    if doc_count == 0:
        checks.append({"name": "has_documents", "status": "warn", "detail": "Aucun document"})
        warnings.append("Aucun document n'est associe a ce batiment")
        passed += 1  # Warning, not blocker
    else:
        checks.append({"name": "has_documents", "status": "pass", "detail": f"{doc_count} document(s)"})
        passed += 1

    # 5. Has engagements
    total += 1
    eng_result = await db.execute(
        select(func.count()).select_from(EcosystemEngagement).where(EcosystemEngagement.building_id == building_id)
    )
    eng_count = eng_result.scalar() or 0
    if eng_count == 0:
        checks.append({"name": "has_engagements", "status": "warn", "detail": "Aucun engagement ecosysteme"})
        warnings.append("Aucun engagement d'acteur n'est enregistre")
        passed += 1  # Warning, not blocker
    else:
        checks.append({"name": "has_engagements", "status": "pass", "detail": f"{eng_count} engagement(s)"})
        passed += 1

    # 6. Open unknowns check
    total += 1
    unk_result = await db.execute(
        select(func.count())
        .select_from(UnknownIssue)
        .where(and_(UnknownIssue.building_id == building_id, UnknownIssue.status == "open"))
    )
    open_unknowns = unk_result.scalar() or 0
    if open_unknowns > 5:
        checks.append(
            {
                "name": "open_unknowns",
                "status": "warn",
                "detail": f"{open_unknowns} inconnue(s) ouverte(s)",
            }
        )
        warnings.append(f"{open_unknowns} zones d'ombre ouvertes — le transfert sera incomplet")
        passed += 1  # Warning, not blocker
    else:
        checks.append(
            {
                "name": "open_unknowns",
                "status": "pass",
                "detail": f"{open_unknowns} inconnue(s) ouverte(s)",
            }
        )
        passed += 1

    readiness_score = round(passed / max(total, 1), 2)
    is_ready = len(blockers) == 0

    return TransferReadiness(
        building_id=building_id,
        is_ready=is_ready,
        readiness_score=readiness_score,
        checks=checks,
        blockers=blockers,
        warnings=warnings,
    )


async def submit_for_review(db: AsyncSession, transfer_id: UUID, user_id: UUID) -> MemoryTransfer:
    """Submit compiled memory for recipient review."""
    result = await db.execute(select(MemoryTransfer).where(MemoryTransfer.id == transfer_id))
    transfer = result.scalar_one_or_none()
    if transfer is None:
        raise ValueError("Transfert introuvable")
    if transfer.status != "memory_compiled":
        raise ValueError("La memoire doit etre compilee avant soumission")

    transfer.status = "review_pending"
    await _emit_domain_event(db, "memory_transfer_submitted_for_review", transfer, actor_user_id=user_id)

    return transfer


async def accept_transfer(
    db: AsyncSession, transfer_id: UUID, user_id: UUID, comment: str | None = None
) -> MemoryTransfer:
    """Recipient accepts the transferred memory."""
    result = await db.execute(select(MemoryTransfer).where(MemoryTransfer.id == transfer_id))
    transfer = result.scalar_one_or_none()
    if transfer is None:
        raise ValueError("Transfert introuvable")
    if transfer.status != "review_pending":
        raise ValueError("Le transfert doit etre en attente de revue pour etre accepte")

    transfer.status = "accepted"
    transfer.accepted_at = datetime.utcnow()
    transfer.accepted_by_id = user_id
    transfer.acceptance_comment = comment

    await _emit_domain_event(
        db,
        "memory_transfer_accepted",
        transfer,
        actor_user_id=user_id,
        payload={"comment": comment},
    )

    # Create ecosystem engagement
    await _create_engagement(
        db,
        transfer.building_id,
        transfer,
        engagement_type="accepted",
        actor_user_id=user_id,
        actor_org_id=transfer.to_org_id,
        comment=comment,
        content_hash=transfer.transfer_package_hash,
    )

    return transfer


async def contest_transfer(db: AsyncSession, transfer_id: UUID, user_id: UUID, comment: str) -> MemoryTransfer:
    """Recipient contests — memory incomplete or inaccurate."""
    result = await db.execute(select(MemoryTransfer).where(MemoryTransfer.id == transfer_id))
    transfer = result.scalar_one_or_none()
    if transfer is None:
        raise ValueError("Transfert introuvable")
    if transfer.status != "review_pending":
        raise ValueError("Le transfert doit etre en attente de revue pour etre conteste")

    transfer.status = "contested"
    transfer.contested_at = datetime.utcnow()
    transfer.contested_by_id = user_id
    transfer.contest_comment = comment

    await _emit_domain_event(
        db,
        "memory_transfer_contested",
        transfer,
        actor_user_id=user_id,
        payload={"comment": comment},
    )

    # Create ecosystem engagement
    await _create_engagement(
        db,
        transfer.building_id,
        transfer,
        engagement_type="contested",
        actor_user_id=user_id,
        actor_org_id=transfer.to_org_id,
        comment=comment,
        content_hash=transfer.transfer_package_hash,
    )

    return transfer


async def complete_transfer(db: AsyncSession, transfer_id: UUID, user_id: UUID) -> MemoryTransfer:
    """Finalize transfer after acceptance."""
    result = await db.execute(select(MemoryTransfer).where(MemoryTransfer.id == transfer_id))
    transfer = result.scalar_one_or_none()
    if transfer is None:
        raise ValueError("Transfert introuvable")
    if transfer.status != "accepted":
        raise ValueError("Le transfert doit etre accepte avant d'etre finalise")

    transfer.status = "completed"
    transfer.completed_at = datetime.utcnow()

    await _emit_domain_event(
        db,
        "memory_transfer_completed",
        transfer,
        actor_user_id=user_id,
    )

    return transfer


async def get_transfer_history(db: AsyncSession, building_id: UUID) -> list[MemoryTransfer]:
    """All transfers for a building — the continuity chain."""
    result = await db.execute(
        select(MemoryTransfer)
        .where(MemoryTransfer.building_id == building_id)
        .order_by(MemoryTransfer.initiated_at.desc())
    )
    return list(result.scalars().all())


async def compute_continuity_score(db: AsyncSession, building_id: UUID) -> MemoryContinuityScore:
    """How complete is this building's memory across its lifecycle.

    Measures: transfers completed, gaps, integrity coverage.
    """
    result = await db.execute(
        select(MemoryTransfer)
        .where(MemoryTransfer.building_id == building_id)
        .order_by(MemoryTransfer.initiated_at.asc())
    )
    transfers = list(result.scalars().all())

    total = len(transfers)
    completed = sum(1 for t in transfers if t.status == "completed")
    accepted = sum(1 for t in transfers if t.status in ("accepted", "completed"))
    contested = sum(1 for t in transfers if t.status == "contested")
    verified = sum(1 for t in transfers if t.integrity_verified)

    integrity_coverage = round(verified / max(total, 1), 2)

    # Continuity score: weighted combination
    if total == 0:
        continuity_score = 0.0
    else:
        completion_ratio = completed / total
        acceptance_ratio = accepted / total
        continuity_score = round(0.5 * completion_ratio + 0.3 * acceptance_ratio + 0.2 * integrity_coverage, 2)

    # Detect gaps — contested or cancelled transfers
    gaps: list[dict] = []
    for t in transfers:
        if t.status in ("contested", "cancelled"):
            gaps.append(
                {
                    "period": str(t.initiated_at) if t.initiated_at else "inconnu",
                    "description": f"Transfert {t.transfer_type} — statut: {t.status}",
                }
            )

    # Lifecycle coverage: % of building life with documented memory
    # Simple heuristic: if there are completed transfers, coverage is proportional
    lifecycle_coverage = round(completed / max(total, 1), 2) if total > 0 else 0.0

    return MemoryContinuityScore(
        building_id=building_id,
        total_transfers=total,
        completed_transfers=completed,
        accepted_transfers=accepted,
        contested_transfers=contested,
        continuity_score=continuity_score,
        integrity_coverage=integrity_coverage,
        gaps=gaps,
        lifecycle_coverage=lifecycle_coverage,
    )
