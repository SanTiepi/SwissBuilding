"""Rituals of Truth service.

8 governed acts that change the truth status of an artifact or building state:
validate, freeze, publish, transfer, acknowledge, reopen, supersede, receipt.
Every ritual is traceable: who, when, what, why.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.truth_ritual import TruthRitual

logger = logging.getLogger(__name__)

VALID_RITUAL_TYPES = {"validate", "freeze", "publish", "transfer", "acknowledge", "reopen", "supersede", "receipt"}
VALID_TARGET_TYPES = {
    "evidence",
    "claim",
    "decision",
    "publication",
    "document",
    "extraction",
    "pack",
    "passport",
    "case",
}


def compute_content_hash(content: str | dict | list) -> str:
    """Compute SHA-256 hash of content."""
    if isinstance(content, (dict, list)):
        content = json.dumps(content, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _validate_ritual_inputs(ritual_type: str, target_type: str) -> None:
    if ritual_type not in VALID_RITUAL_TYPES:
        raise ValueError(
            f"Invalid ritual_type '{ritual_type}'. Must be one of: {', '.join(sorted(VALID_RITUAL_TYPES))}"
        )
    if target_type not in VALID_TARGET_TYPES:
        raise ValueError(
            f"Invalid target_type '{target_type}'. Must be one of: {', '.join(sorted(VALID_TARGET_TYPES))}"
        )


async def validate(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    validated_by_id: UUID,
    org_id: UUID,
    reason: str | None = None,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Expert validates an artifact. Records the ritual."""
    _validate_ritual_inputs("validate", target_type)
    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="validate",
        performed_by_id=validated_by_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        case_id=case_id,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def freeze(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    frozen_by_id: UUID,
    org_id: UUID,
    content: str | dict | list | None = None,
    reason: str | None = None,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Freeze an artifact for a specific purpose. Computes content hash. No further edits allowed."""
    _validate_ritual_inputs("freeze", target_type)
    content_hash = compute_content_hash(content) if content is not None else None
    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="freeze",
        performed_by_id=frozen_by_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        case_id=case_id,
        content_hash=content_hash,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def publish(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    published_by_id: UUID,
    org_id: UUID,
    content: str | dict | list | None = None,
    recipient_type: str | None = None,
    recipient_id: UUID | None = None,
    delivery_method: str | None = None,
    reason: str | None = None,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Publish an artifact. Computes hash, increments version.

    Logs a warning if no prior conformance check exists for this target.
    """
    _validate_ritual_inputs("publish", target_type)

    # Check if a conformance check exists for this target
    try:
        from app.models.conformance import ConformanceCheck

        existing = await db.execute(
            select(ConformanceCheck).where(
                ConformanceCheck.building_id == building_id,
                ConformanceCheck.target_type == target_type,
                ConformanceCheck.target_id == target_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            logger.warning(
                "Publish ritual for %s/%s on building %s: aucune verification de conformite prealable",
                target_type,
                target_id,
                building_id,
            )
    except Exception:
        pass  # Non-blocking — conformance check is advisory

    # Compute next version for this target
    version = await _next_version(db, building_id, target_type, target_id)
    content_hash = compute_content_hash(content) if content is not None else None

    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="publish",
        performed_by_id=published_by_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        case_id=case_id,
        content_hash=content_hash,
        version=version,
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        delivery_method=delivery_method,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def transfer(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    transferred_by_id: UUID,
    org_id: UUID,
    recipient_type: str,
    recipient_id: UUID,
    delivery_method: str,
    content: str | dict | list | None = None,
    reason: str | None = None,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Transfer a sovereign artifact to a recipient. Requires receipt."""
    _validate_ritual_inputs("transfer", target_type)
    content_hash = compute_content_hash(content) if content is not None else None

    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="transfer",
        performed_by_id=transferred_by_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        case_id=case_id,
        content_hash=content_hash,
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        delivery_method=delivery_method,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def acknowledge(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    acknowledged_by_id: UUID,
    org_id: UUID,
    receipt_hash: str | None = None,
    reason: str | None = None,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Acknowledge receipt of an artifact. Records receipt proof."""
    _validate_ritual_inputs("acknowledge", target_type)

    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="acknowledge",
        performed_by_id=acknowledged_by_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        case_id=case_id,
        acknowledged_by_id=acknowledged_by_id,
        receipt_hash=receipt_hash,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def reopen(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    reopened_by_id: UUID,
    org_id: UUID,
    reason: str,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Reopen a previously frozen or published artifact. Reason is required (never silent)."""
    _validate_ritual_inputs("reopen", target_type)
    if not reason or not reason.strip():
        raise ValueError("Reopen ritual requires a non-empty reason")

    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="reopen",
        performed_by_id=reopened_by_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        case_id=case_id,
        reopen_reason=reason,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def supersede(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    superseded_by_id: UUID,
    org_id: UUID,
    new_target_id: UUID,
    reason: str | None = None,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Mark an artifact as superseded by a newer version. Links old -> new explicitly."""
    _validate_ritual_inputs("supersede", target_type)

    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="supersede",
        performed_by_id=superseded_by_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        case_id=case_id,
        supersedes_id=new_target_id,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def receipt(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
    recipient_id: UUID,
    org_id: UUID,
    receipt_hash: str,
    delivery_method: str,
    performed_by_id: UUID | None = None,
    case_id: UUID | None = None,
) -> TruthRitual:
    """Record cryptographic or timestamped proof of delivery."""
    _validate_ritual_inputs("receipt", target_type)

    ritual = TruthRitual(
        building_id=building_id,
        ritual_type="receipt",
        performed_by_id=performed_by_id or recipient_id,
        organization_id=org_id,
        target_type=target_type,
        target_id=target_id,
        case_id=case_id,
        receipt_hash=receipt_hash,
        recipient_id=recipient_id,
        delivery_method=delivery_method,
        performed_at=datetime.now(UTC),
    )
    db.add(ritual)
    await db.flush()
    return ritual


async def get_ritual_history(
    db: AsyncSession,
    building_id: UUID | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    ritual_type: str | None = None,
) -> list[TruthRitual]:
    """Get ritual history with optional filters."""
    query = select(TruthRitual)
    if building_id is not None:
        query = query.where(TruthRitual.building_id == building_id)
    if target_type is not None:
        query = query.where(TruthRitual.target_type == target_type)
    if target_id is not None:
        query = query.where(TruthRitual.target_id == target_id)
    if ritual_type is not None:
        query = query.where(TruthRitual.ritual_type == ritual_type)
    query = query.order_by(TruthRitual.performed_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def _next_version(
    db: AsyncSession,
    building_id: UUID,
    target_type: str,
    target_id: UUID,
) -> int:
    """Compute the next version number for publish rituals on this target."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.coalesce(func.max(TruthRitual.version), 0)).where(
            TruthRitual.building_id == building_id,
            TruthRitual.target_type == target_type,
            TruthRitual.target_id == target_id,
            TruthRitual.ritual_type == "publish",
        )
    )
    current_max = result.scalar() or 0
    return current_max + 1
