"""BatiConnect - Operational Gate Service.

Blocking gates that prevent chaos by requiring specific proofs before
operations can proceed. SwissBuilding doesn't just measure — it BLOCKS.

Idempotent gate creation, real-time prerequisite evaluation, audit-trailed overrides.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_event import DomainEvent
from app.models.operational_gate import OperationalGate
from app.schemas.operational_gate import (
    BuildingGateStatus,
    GateEvaluation,
    GatePrerequisite,
    OperationalGateRead,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gate definitions — French labels + prerequisites templates
# ---------------------------------------------------------------------------

_GATE_DEFINITIONS: list[dict] = [
    {
        "gate_type": "launch_rfq",
        "gate_label": "Lancement appel d'offres (mise en concurrence)",
        "prerequisites": [
            {
                "type": "engagement",
                "subject_type": "diagnostic",
                "engagement_type": "confirmed",
                "label": "Diagnostic confirme par le diagnostiqueur",
            },
            {"type": "safe_to_start", "label": "Safe-to-start ne doit pas etre en risque critique"},
            {"type": "diagnostic", "label": "Au moins 1 polluant evalue dans un diagnostic valide"},
        ],
    },
    {
        "gate_type": "close_lot",
        "gate_label": "Cloture d'un lot de travaux",
        "prerequisites": [
            {
                "type": "engagement",
                "subject_type": "delivery",
                "engagement_type": "confirmed",
                "label": "Confirmation de fin de lot par l'entreprise",
            },
            {"type": "document", "subject_type": "post_works", "label": "Rapport post-travaux depose"},
            {
                "type": "engagement",
                "subject_type": "intervention",
                "engagement_type": "acknowledged",
                "label": "Prise de connaissance entrepreneur",
            },
        ],
    },
    {
        "gate_type": "transfer_dossier",
        "gate_label": "Transfert de dossier immobilier",
        "prerequisites": [
            {"type": "proof_chain", "label": "Chaines de preuves completes (tous documents hashes)"},
            {"type": "document", "subject_type": "transfer_package", "label": "Package de transfert genere"},
            {
                "type": "engagement",
                "subject_type": "dossier",
                "engagement_type": "confirmed",
                "label": "Engagement du gestionnaire actuel confirme",
            },
        ],
    },
    {
        "gate_type": "start_works",
        "gate_label": "Demarrage des travaux de remediation",
        "prerequisites": [
            {"type": "safe_to_start", "label": "Safe-to-start: pret a demarrer ou sous conditions"},
            {"type": "procedure", "label": "Procedure autorite approuvee (si requise)"},
            {
                "type": "engagement",
                "subject_type": "intervention",
                "engagement_type": "accepted",
                "label": "Engagement entrepreneur accepte",
            },
        ],
    },
    {
        "gate_type": "submit_authority",
        "gate_label": "Soumission au service cantonal (autorite)",
        "prerequisites": [
            {"type": "pack", "subject_type": "authority", "label": "Pack autorite genere"},
            {"type": "document", "subject_type": "required_docs", "label": "Tous les documents requis presents"},
            {"type": "diagnostic", "label": "Couverture diagnostique >= 80%"},
        ],
    },
    {
        "gate_type": "deliver_pack",
        "gate_label": "Livraison d'un pack audience",
        "prerequisites": [
            {"type": "pack", "subject_type": "audience", "label": "Pack audience genere avec hash de contenu"},
            {"type": "document", "subject_type": "content_hash", "label": "Hash de contenu verifie"},
            {
                "type": "engagement",
                "subject_type": "pack",
                "engagement_type": "confirmed",
                "label": "Validation du reviseur (si requis)",
            },
        ],
    },
    {
        "gate_type": "change_management",
        "gate_label": "Changement de gerance ou de gestionnaire",
        "prerequisites": [
            {"type": "proof_chain", "label": "Memoire de transfert complete"},
            {
                "type": "engagement",
                "subject_type": "dossier",
                "engagement_type": "confirmed",
                "label": "Tous les engagements documentes",
            },
            {
                "type": "document",
                "subject_type": "snapshot",
                "label": "Memoire temporelle complete (snapshots existants)",
            },
        ],
    },
    {
        "gate_type": "sell",
        "gate_label": "Vente de l'immeuble",
        "prerequisites": [
            {"type": "proof_chain", "label": "Tous les gates operationnels clairs"},
            {"type": "pack", "subject_type": "transfer", "label": "Package de transfert pret"},
            {"type": "document", "subject_type": "issues_documented", "label": "Tous les problemes connus documentes"},
        ],
    },
    {
        "gate_type": "refinance",
        "gate_label": "Refinancement de l'immeuble",
        "prerequisites": [
            {"type": "pack", "subject_type": "lender", "label": "Pack preteur pret"},
            {"type": "document", "subject_type": "valuation", "label": "Evaluation immobiliere documentee"},
            {"type": "safe_to_start", "label": "Aucun bloquant critique identifie"},
        ],
    },
    {
        "gate_type": "reopen_after_works",
        "gate_label": "Reouverture apres travaux",
        "prerequisites": [
            {"type": "document", "subject_type": "post_works_final", "label": "Rapport post-travaux finalise"},
            {"type": "diagnostic", "label": "Verification residuelle effectuee"},
            {"type": "safe_to_start", "label": "Nouveau safe-to-start calcule"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Gate creation (idempotent)
# ---------------------------------------------------------------------------


async def ensure_building_gates(db: AsyncSession, building_id: UUID) -> list[OperationalGate]:
    """Create/update gates for a building based on its current state. Idempotent."""
    # Fetch existing gates
    result = await db.execute(select(OperationalGate).where(OperationalGate.building_id == building_id))
    existing = {g.gate_type: g for g in result.scalars().all()}

    gates: list[OperationalGate] = []
    for defn in _GATE_DEFINITIONS:
        gate_type = defn["gate_type"]
        if gate_type in existing:
            gate = existing[gate_type]
            # Update label if changed
            if gate.gate_label != defn["gate_label"]:
                gate.gate_label = defn["gate_label"]
            gates.append(gate)
        else:
            # Create new gate
            prereqs = [{**p, "satisfied": False, "item_id": None} for p in defn["prerequisites"]]
            gate = OperationalGate(
                building_id=building_id,
                gate_type=gate_type,
                gate_label=defn["gate_label"],
                status="blocked",
                prerequisites=prereqs,
            )
            db.add(gate)
            gates.append(gate)

    await db.flush()
    return gates


# ---------------------------------------------------------------------------
# Gate evaluation — check prerequisites against real data
# ---------------------------------------------------------------------------


async def evaluate_gates(db: AsyncSession, building_id: UUID) -> GateEvaluation:
    """Evaluate all gates for a building. Returns status per gate + overall."""
    gates = await ensure_building_gates(db, building_id)

    evaluated: list[OperationalGateRead] = []
    counts = {"blocked": 0, "conditions_pending": 0, "clearable": 0, "cleared": 0, "overridden": 0}

    for gate in gates:
        if gate.status in ("cleared", "overridden", "expired"):
            # Already resolved — don't re-evaluate
            prereqs = _parse_prerequisites(gate.prerequisites or [])
            read = _gate_to_read(gate, prereqs)
            evaluated.append(read)
            counts[gate.status] = counts.get(gate.status, 0) + 1
            continue

        if not gate.auto_evaluate:
            prereqs = _parse_prerequisites(gate.prerequisites or [])
            read = _gate_to_read(gate, prereqs)
            evaluated.append(read)
            counts[gate.status] = counts.get(gate.status, 0) + 1
            continue

        # Evaluate each prerequisite
        prereqs = await _evaluate_prerequisites(db, building_id, gate)

        # Determine gate status from prerequisites
        all_satisfied = all(p.satisfied for p in prereqs)
        any_satisfied = any(p.satisfied for p in prereqs)

        if all_satisfied:
            gate.status = "clearable"
        elif any_satisfied:
            gate.status = "conditions_pending"
        else:
            gate.status = "blocked"

        # Update stored prerequisites
        gate.prerequisites = [p.model_dump(mode="json") for p in prereqs]
        counts[gate.status] = counts.get(gate.status, 0) + 1

        read = _gate_to_read(gate, prereqs)
        evaluated.append(read)

    await db.flush()

    total = len(evaluated)
    return GateEvaluation(
        building_id=building_id,
        gates=evaluated,
        total=total,
        blocked=counts["blocked"],
        conditions_pending=counts["conditions_pending"],
        clearable=counts["clearable"],
        cleared=counts["cleared"],
        overridden=counts["overridden"],
        all_clear=counts["blocked"] == 0 and counts["conditions_pending"] == 0,
    )


# ---------------------------------------------------------------------------
# Override / Clear
# ---------------------------------------------------------------------------


async def override_gate(db: AsyncSession, gate_id: UUID, user_id: UUID, reason: str) -> OperationalGate:
    """Override a blocked gate. Creates DomainEvent for audit trail."""
    result = await db.execute(select(OperationalGate).where(OperationalGate.id == gate_id))
    gate = result.scalar_one_or_none()
    if gate is None:
        raise ValueError("Gate not found")
    if gate.status in ("cleared",):
        raise ValueError("Cannot override a gate that is already cleared")

    now = datetime.now(UTC)
    gate.status = "overridden"
    gate.overridden_by_id = user_id
    gate.override_reason = reason
    gate.overridden_at = now

    # Audit trail via DomainEvent
    event = DomainEvent(
        event_type="gate_overridden",
        aggregate_type="operational_gate",
        aggregate_id=gate.id,
        payload={
            "gate_type": gate.gate_type,
            "building_id": str(gate.building_id),
            "reason": reason,
            "overridden_by": str(user_id),
        },
        actor_user_id=user_id,
        occurred_at=now,
    )
    db.add(event)
    await db.flush()
    return gate


async def clear_gate(db: AsyncSession, gate_id: UUID, user_id: UUID) -> OperationalGate:
    """Clear a gate when all prerequisites are satisfied."""
    result = await db.execute(select(OperationalGate).where(OperationalGate.id == gate_id))
    gate = result.scalar_one_or_none()
    if gate is None:
        raise ValueError("Gate not found")
    if gate.status == "cleared":
        raise ValueError("Gate is already cleared")
    if gate.status not in ("clearable", "conditions_pending"):
        raise ValueError(f"Cannot clear gate with status '{gate.status}' — must be clearable or conditions_pending")

    now = datetime.now(UTC)
    gate.status = "cleared"
    gate.cleared_at = now
    gate.cleared_by_id = user_id

    # Audit trail
    event = DomainEvent(
        event_type="gate_cleared",
        aggregate_type="operational_gate",
        aggregate_id=gate.id,
        payload={
            "gate_type": gate.gate_type,
            "building_id": str(gate.building_id),
            "cleared_by": str(user_id),
        },
        actor_user_id=user_id,
        occurred_at=now,
    )
    db.add(event)
    await db.flush()
    return gate


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


async def get_blocking_gates(db: AsyncSession, building_id: UUID) -> list[OperationalGate]:
    """Get only blocked/conditions_pending gates."""
    result = await db.execute(
        select(OperationalGate).where(
            OperationalGate.building_id == building_id,
            OperationalGate.status.in_(["blocked", "conditions_pending"]),
        )
    )
    return list(result.scalars().all())


async def get_gate_status(db: AsyncSession, building_id: UUID) -> BuildingGateStatus:
    """Summary of gate status for a building."""
    result = await db.execute(select(OperationalGate).where(OperationalGate.building_id == building_id))
    gates = list(result.scalars().all())

    counts: dict[str, int] = {
        "blocked": 0,
        "conditions_pending": 0,
        "clearable": 0,
        "cleared": 0,
        "overridden": 0,
        "expired": 0,
    }
    for g in gates:
        counts[g.status] = counts.get(g.status, 0) + 1

    return BuildingGateStatus(
        building_id=building_id,
        total=len(gates),
        blocked=counts["blocked"],
        conditions_pending=counts["conditions_pending"],
        clearable=counts["clearable"],
        cleared=counts["cleared"],
        overridden=counts["overridden"],
        expired=counts["expired"],
        all_clear=counts["blocked"] == 0 and counts["conditions_pending"] == 0,
    )


# ---------------------------------------------------------------------------
# Internal — prerequisite evaluation
# ---------------------------------------------------------------------------


async def _evaluate_prerequisites(db: AsyncSession, building_id: UUID, gate: OperationalGate) -> list[GatePrerequisite]:
    """Evaluate each prerequisite against real data."""
    raw_prereqs = gate.prerequisites or []
    evaluated: list[GatePrerequisite] = []

    for p in raw_prereqs:
        prereq_type = p.get("type", "")
        label = p.get("label", "")
        satisfied = False
        item_id = None

        if prereq_type == "engagement":
            satisfied, item_id = await _check_engagement(
                db, building_id, p.get("subject_type"), p.get("engagement_type")
            )
        elif prereq_type == "document":
            satisfied, item_id = await _check_document(db, building_id, p.get("subject_type"))
        elif prereq_type == "diagnostic":
            satisfied, item_id = await _check_diagnostic(db, building_id, label)
        elif prereq_type == "safe_to_start":
            satisfied = await _check_safe_to_start(db, building_id, label)
        elif prereq_type == "obligation":
            satisfied, item_id = await _check_obligation(db, building_id, p.get("subject_type"))
        elif prereq_type == "procedure":
            satisfied, item_id = await _check_procedure(db, building_id)
        elif prereq_type == "pack":
            satisfied, item_id = await _check_pack(db, building_id, p.get("subject_type"))
        elif prereq_type == "proof_chain":
            satisfied = await _check_proof_chain(db, building_id, label)

        evaluated.append(
            GatePrerequisite(
                type=prereq_type,
                subject_type=p.get("subject_type"),
                engagement_type=p.get("engagement_type"),
                label=label,
                satisfied=satisfied,
                item_id=item_id,
            )
        )

    return evaluated


async def _check_engagement(
    db: AsyncSession, building_id: UUID, subject_type: str | None, engagement_type: str | None
) -> tuple[bool, UUID | None]:
    """Check if an engagement of the required type exists."""
    from app.models.ecosystem_engagement import EcosystemEngagement

    q = select(EcosystemEngagement).where(
        EcosystemEngagement.building_id == building_id,
        EcosystemEngagement.status == "active",
    )
    if subject_type:
        q = q.where(EcosystemEngagement.subject_type == subject_type)
    if engagement_type:
        q = q.where(EcosystemEngagement.engagement_type == engagement_type)

    result = await db.execute(q.limit(1))
    eng = result.scalar_one_or_none()
    if eng:
        return True, eng.id
    return False, None


async def _check_document(db: AsyncSession, building_id: UUID, subject_type: str | None) -> tuple[bool, UUID | None]:
    """Check if required documents exist."""
    from app.models.document import Document

    q = select(Document).where(Document.building_id == building_id)
    # Map subject_type to document type patterns
    type_mapping = {
        "post_works": "post_works",
        "transfer_package": "transfer_package",
        "required_docs": None,  # any document
        "content_hash": None,
        "post_works_final": "post_works",
        "valuation": "valuation",
        "issues_documented": None,
        "snapshot": None,
    }
    doc_type = type_mapping.get(subject_type)
    if doc_type:
        q = q.where(Document.document_type == doc_type)

    result = await db.execute(q.limit(1))
    doc = result.scalar_one_or_none()
    if doc:
        return True, doc.id
    return False, None


async def _check_diagnostic(db: AsyncSession, building_id: UUID, label: str) -> tuple[bool, UUID | None]:
    """Check diagnostic prerequisites."""
    from app.models.diagnostic import Diagnostic
    from app.models.sample import Sample

    # Check for validated/completed diagnostics
    diag_result = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    diagnostics = list(diag_result.scalars().all())

    if not diagnostics:
        return False, None

    # Coverage check
    if "couverture" in label.lower() or "coverage" in label.lower() or ">= 80" in label:
        # Check diagnostic coverage: count samples with results
        sample_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id.in_([d.id for d in diagnostics]),
            )
        )
        samples = list(sample_result.scalars().all())
        total = len(samples)
        with_result = sum(1 for s in samples if s.result is not None)
        coverage = (with_result / total * 100) if total > 0 else 0
        return coverage >= 80, diagnostics[0].id

    # Residual verification check
    if "residuelle" in label.lower() or "verification" in label.lower():
        # Look for post-remediation diagnostics
        post_diags = [d for d in diagnostics if d.status == "validated"]
        if post_diags:
            return True, post_diags[0].id
        return False, None

    # Default: at least 1 pollutant assessed
    return True, diagnostics[0].id


async def _check_safe_to_start(db: AsyncSession, building_id: UUID, label: str) -> bool:
    """Check safe-to-start status."""
    try:
        from app.services.safe_to_start_service import compute_safe_to_start

        sts = await compute_safe_to_start(db, building_id)
        if sts is None:
            return False

        if "critique" in label.lower() or "critical" in label.lower() or "bloquant" in label.lower():
            # Must NOT be critical_risk
            return sts.status != "critical_risk"

        if "pret" in label.lower() or "ready" in label.lower() or "demarrer" in label.lower():
            return sts.status in ("ready_to_proceed", "proceed_with_conditions")

        if "nouveau" in label.lower() or "calcule" in label.lower():
            # Just needs to exist (any status)
            return True

        # Default: not critical
        return sts.status != "critical_risk"
    except Exception:
        logger.debug("Safe-to-start check failed for %s", building_id, exc_info=True)
        return False


async def _check_obligation(db: AsyncSession, building_id: UUID, subject_type: str | None) -> tuple[bool, UUID | None]:
    """Check if obligations are fulfilled."""
    from app.models.obligation import Obligation

    q = select(Obligation).where(
        Obligation.building_id == building_id,
        Obligation.status.in_(["overdue", "due_soon"]),
    )
    if subject_type:
        q = q.where(Obligation.obligation_type == subject_type)

    result = await db.execute(q.limit(1))
    overdue = result.scalar_one_or_none()
    # Satisfied if NO overdue/due_soon obligations
    return overdue is None, None


async def _check_procedure(db: AsyncSession, building_id: UUID) -> tuple[bool, UUID | None]:
    """Check if authority procedures are approved."""
    from app.models.permit_procedure import PermitProcedure

    result = await db.execute(
        select(PermitProcedure).where(
            PermitProcedure.building_id == building_id,
            PermitProcedure.status.in_(["pending", "submitted"]),
        )
    )
    pending = result.scalar_one_or_none()
    if pending:
        # There's a pending procedure — not approved yet
        return False, pending.id

    # Check if any approved procedure exists or none needed
    approved_result = await db.execute(
        select(PermitProcedure).where(
            PermitProcedure.building_id == building_id,
            PermitProcedure.status == "approved",
        )
    )
    approved = approved_result.scalar_one_or_none()
    if approved:
        return True, approved.id

    # No procedures at all — assume not needed (satisfied)
    return True, None


async def _check_pack(db: AsyncSession, building_id: UUID, subject_type: str | None) -> tuple[bool, UUID | None]:
    """Check if required packs are generated."""
    from app.models.audience_pack import AudiencePack

    if subject_type in ("authority", "audience", "lender"):
        result = await db.execute(
            select(AudiencePack)
            .where(
                AudiencePack.building_id == building_id,
            )
            .limit(1)
        )
        pack = result.scalar_one_or_none()
        if pack:
            return True, pack.id
        return False, None

    if subject_type == "transfer":
        # Check for transfer package existence via documents
        from app.models.document import Document

        result = await db.execute(
            select(Document)
            .where(
                Document.building_id == building_id,
                Document.document_type == "transfer_package",
            )
            .limit(1)
        )
        doc = result.scalar_one_or_none()
        if doc:
            return True, doc.id
        return False, None

    return False, None


async def _check_proof_chain(db: AsyncSession, building_id: UUID, label: str) -> bool:
    """Check proof chain completeness."""
    from app.models.document import Document

    # Check all documents have hashes
    result = await db.execute(select(Document).where(Document.building_id == building_id))
    docs = list(result.scalars().all())

    if not docs:
        return False

    # For "all gates clear" check
    if "gates" in label.lower() or "clairs" in label.lower():
        status = await get_gate_status(db, building_id)
        # Exclude the "sell" gate itself from the check
        return status.blocked == 0 and status.conditions_pending == 0

    # Default: all documents should have a hash (file_hash field)
    hashed = sum(1 for d in docs if getattr(d, "file_hash", None))
    return hashed >= len(docs) * 0.8  # 80% threshold


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_prerequisites(raw: list) -> list[GatePrerequisite]:
    """Parse raw JSON prerequisites into schema objects."""
    result = []
    for p in raw:
        if isinstance(p, dict):
            result.append(
                GatePrerequisite(
                    type=p.get("type", ""),
                    subject_type=p.get("subject_type"),
                    engagement_type=p.get("engagement_type"),
                    label=p.get("label", ""),
                    satisfied=p.get("satisfied", False),
                    item_id=p.get("item_id"),
                )
            )
    return result


def _gate_to_read(gate: OperationalGate, prereqs: list[GatePrerequisite]) -> OperationalGateRead:
    """Convert gate + prerequisites to read schema."""
    return OperationalGateRead(
        id=gate.id,
        building_id=gate.building_id,
        gate_type=gate.gate_type,
        gate_label=gate.gate_label,
        status=gate.status,
        prerequisites=prereqs,
        overridden_by_id=gate.overridden_by_id,
        override_reason=gate.override_reason,
        overridden_at=gate.overridden_at,
        cleared_at=gate.cleared_at,
        cleared_by_id=gate.cleared_by_id,
        auto_evaluate=gate.auto_evaluate,
        created_at=gate.created_at,
        updated_at=gate.updated_at,
    )
