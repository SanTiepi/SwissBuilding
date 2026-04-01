"""Passport Envelope Service — sovereign, versioned, receipted, transferable passports.

The envelope wraps a building passport snapshot into an immutable, hashable,
transferable object that survives sale, handoff, diligence, insurer review,
management change, and later re-import.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.passport_envelope import BuildingPassportEnvelope, PassportTransferReceipt
from app.services import ritual_service

logger = logging.getLogger(__name__)

# Sections that map to passport_data top-level keys
_ALL_SECTIONS = [
    "knowledge_state",
    "completeness",
    "readiness",
    "blind_spots",
    "contradictions",
    "evidence_coverage",
    "diagnostic_publications",
    "pollutant_coverage",
    "passport_grade",
]

# Financial keys to redact
_FINANCIAL_KEYS = frozenset(
    {
        "total_amount_chf",
        "cost",
        "amount",
        "price",
        "amount_chf",
        "total_expenses_chf",
        "total_income_chf",
        "claimed_amount_chf",
        "approved_amount_chf",
        "paid_amount_chf",
        "insured_value_chf",
        "premium_annual_chf",
    }
)

# Personal data keys to redact
_PERSONAL_KEYS = frozenset(
    {
        "owner_name",
        "contact_name",
        "email",
        "phone",
        "address_personal",
    }
)


def _compute_hash(data: dict) -> str:
    """Compute SHA-256 hash of a dict."""
    canonical = json.dumps(data, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _redact_dict(data: dict, keys_to_redact: frozenset) -> dict:
    """Recursively redact specified keys in a dict."""
    redacted = {}
    for key, value in data.items():
        if key in keys_to_redact:
            redacted[key] = "[redacted]"
        elif isinstance(value, dict):
            redacted[key] = _redact_dict(value, keys_to_redact)
        elif isinstance(value, list):
            redacted[key] = [_redact_dict(v, keys_to_redact) if isinstance(v, dict) else v for v in value]
        else:
            redacted[key] = value
    return redacted


def _apply_redaction(passport_data: dict, profile: str) -> tuple[dict, bool, bool]:
    """Apply redaction profile to passport data.

    Returns (redacted_data, financials_redacted, personal_data_redacted).
    """
    financials_redacted = False
    personal_data_redacted = False

    if profile == "none":
        return passport_data, False, False

    result = passport_data
    if profile in ("financial", "detailed"):
        result = _redact_dict(result, _FINANCIAL_KEYS)
        financials_redacted = True

    if profile in ("personal", "detailed"):
        result = _redact_dict(result, _PERSONAL_KEYS)
        personal_data_redacted = True

    return result, financials_redacted, personal_data_redacted


async def _next_version(db: AsyncSession, building_id: UUID) -> int:
    """Get the next version number for a building's envelopes."""
    result = await db.execute(
        select(func.max(BuildingPassportEnvelope.version)).where(BuildingPassportEnvelope.building_id == building_id)
    )
    max_version = result.scalar()
    return (max_version or 0) + 1


async def create_envelope(
    db: AsyncSession,
    building_id: UUID,
    org_id: UUID,
    created_by_id: UUID,
    redaction_profile: str = "none",
    version_label: str | None = None,
) -> BuildingPassportEnvelope:
    """Generate a new passport envelope from current building state.

    Uses passport_service to assemble content, applies redaction profile,
    computes SHA-256 hash, auto-increments version.
    """
    from app.services.passport_service import get_passport_summary

    passport_data = await get_passport_summary(db, building_id)
    if passport_data is None:
        raise ValueError("Building not found")

    # Apply redaction
    redacted_data, fin_redacted, pers_redacted = _apply_redaction(passport_data, redaction_profile)

    # Determine sections included
    sections = [k for k in _ALL_SECTIONS if k in redacted_data]

    # Compute integrity hash on the full (pre-redacted) data
    content_hash = _compute_hash(passport_data)

    version = await _next_version(db, building_id)

    # Mark previous sovereign envelopes as non-sovereign
    prev_result = await db.execute(
        select(BuildingPassportEnvelope).where(
            and_(
                BuildingPassportEnvelope.building_id == building_id,
                BuildingPassportEnvelope.is_sovereign.is_(True),
            )
        )
    )
    for prev in prev_result.scalars().all():
        prev.is_sovereign = False

    envelope = BuildingPassportEnvelope(
        building_id=building_id,
        organization_id=org_id,
        created_by_id=created_by_id,
        version=version,
        version_label=version_label,
        passport_data=redacted_data,
        sections_included=sections,
        content_hash=content_hash,
        redaction_profile=redaction_profile,
        financials_redacted=fin_redacted,
        personal_data_redacted=pers_redacted,
        is_sovereign=True,
        status="draft",
    )
    db.add(envelope)
    return envelope


async def freeze_envelope(
    db: AsyncSession,
    envelope_id: UUID,
    frozen_by_id: UUID,
) -> BuildingPassportEnvelope:
    """Freeze the envelope. No further edits. Content hash verified."""
    envelope = await _get_or_raise(db, envelope_id)
    if envelope.status != "draft":
        raise ValueError(f"Cannot freeze envelope in status '{envelope.status}'")

    # Verify content hash integrity
    current_hash = _compute_hash(envelope.passport_data)
    if current_hash != envelope.content_hash:
        logger.warning(
            "Content hash mismatch for envelope %s: stored=%s, computed=%s",
            envelope_id,
            envelope.content_hash,
            current_hash,
        )

    envelope.status = "frozen"
    envelope.frozen_at = datetime.now(UTC)
    envelope.frozen_by_id = frozen_by_id

    # Record canonical ritual trace
    await ritual_service.freeze(
        db,
        envelope.building_id,
        "passport",
        envelope.id,
        frozen_by_id,
        envelope.organization_id,
        reason="Passport envelope frozen",
    )

    return envelope


async def publish_envelope(
    db: AsyncSession,
    envelope_id: UUID,
    published_by_id: UUID,
) -> BuildingPassportEnvelope:
    """Publish the envelope. Must be frozen first.

    Auto-runs a conformance check against the 'publication' profile.
    The check is advisory — it does not block publication.
    """
    envelope = await _get_or_raise(db, envelope_id)
    if envelope.status != "frozen":
        raise ValueError(f"Cannot publish envelope in status '{envelope.status}' (must be frozen)")

    envelope.status = "published"
    envelope.published_at = datetime.now(UTC)
    envelope.published_by_id = published_by_id

    # Record canonical ritual trace
    await ritual_service.publish(
        db,
        envelope.building_id,
        "passport",
        envelope.id,
        published_by_id,
        envelope.organization_id,
    )

    # Auto-conformance check (advisory — does not block publication)
    try:
        from app.services.conformance_service import run_conformance_check

        check = await run_conformance_check(
            db,
            envelope.building_id,
            "publication",
            target_type="passport",
            target_id=envelope.id,
            checked_by_id=published_by_id,
        )
        logger.info(
            "Auto-conformance on publish envelope %s: %s (score=%.0f%%)",
            envelope_id,
            check.result,
            check.score * 100,
        )
    except Exception:
        logger.warning("Auto-conformance check failed for envelope %s", envelope_id)

    return envelope


async def transfer_envelope(
    db: AsyncSession,
    envelope_id: UUID,
    transferred_by_id: UUID,
    sender_org_id: UUID,
    recipient_type: str,
    recipient_id: UUID | None = None,
    recipient_name: str | None = None,
    delivery_method: str = "in_app",
    notes: str | None = None,
) -> PassportTransferReceipt:
    """Transfer the envelope to a recipient. Creates a TransferReceipt.

    The envelope must be published. Content is locked at this point.
    """
    envelope = await _get_or_raise(db, envelope_id)
    if envelope.status not in ("published", "transferred"):
        raise ValueError(f"Cannot transfer envelope in status '{envelope.status}' (must be published)")

    now = datetime.now(UTC)

    # Update envelope transfer fields
    envelope.status = "transferred"
    envelope.transferred_to_type = recipient_type
    envelope.transferred_to_id = recipient_id
    envelope.transferred_at = now
    envelope.transfer_method = delivery_method

    # Compute delivery proof hash
    delivery_proof = _compute_hash(envelope.passport_data)

    # Create receipt
    receipt = PassportTransferReceipt(
        envelope_id=envelope_id,
        sender_org_id=sender_org_id,
        recipient_org_id=recipient_id if recipient_type == "organization" else None,
        recipient_name=recipient_name,
        sent_at=now,
        delivery_method=delivery_method,
        delivery_proof_hash=delivery_proof,
        notes=notes,
    )
    db.add(receipt)

    # Record canonical ritual trace
    await ritual_service.transfer(
        db,
        envelope.building_id,
        "passport",
        envelope.id,
        transferred_by_id,
        sender_org_id,
        recipient_type=recipient_type,
        recipient_id=recipient_id or transferred_by_id,
        delivery_method=delivery_method,
    )

    return receipt


async def acknowledge_receipt(
    db: AsyncSession,
    receipt_id: UUID,
    acknowledged_by_name: str,
    receipt_hash: str | None = None,
) -> PassportTransferReceipt:
    """Recipient acknowledges receipt of the passport envelope."""
    result = await db.execute(select(PassportTransferReceipt).where(PassportTransferReceipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise ValueError("Transfer receipt not found")
    if receipt.acknowledged:
        raise ValueError("Receipt already acknowledged")

    now = datetime.now(UTC)
    receipt.acknowledged = True
    receipt.acknowledged_at = now
    receipt.acknowledged_by_name = acknowledged_by_name

    # Compute receipt hash from delivery proof + acknowledgment timestamp
    if receipt_hash:
        receipt.receipt_hash = receipt_hash
    else:
        ack_payload = {
            "delivery_proof_hash": receipt.delivery_proof_hash,
            "acknowledged_by": acknowledged_by_name,
            "acknowledged_at": now.isoformat(),
        }
        receipt.receipt_hash = _compute_hash(ack_payload)

    # Also update the envelope
    env_result = await db.execute(
        select(BuildingPassportEnvelope).where(BuildingPassportEnvelope.id == receipt.envelope_id)
    )
    envelope = env_result.scalar_one_or_none()
    if envelope:
        envelope.status = "acknowledged"
        envelope.acknowledged_at = now
        envelope.receipt_hash = receipt.receipt_hash

        # Record canonical ritual trace
        await ritual_service.acknowledge(
            db,
            envelope.building_id,
            "passport",
            envelope.id,
            acknowledged_by_id=envelope.created_by_id,
            org_id=envelope.organization_id,
            receipt_hash=receipt.receipt_hash,
        )

    return receipt


async def supersede_envelope(
    db: AsyncSession,
    old_envelope_id: UUID,
    new_envelope_id: UUID,
    reason: str | None = None,
) -> BuildingPassportEnvelope:
    """Mark old envelope as superseded by new one."""
    old_envelope = await _get_or_raise(db, old_envelope_id)
    new_envelope = await _get_or_raise(db, new_envelope_id)

    if old_envelope.building_id != new_envelope.building_id:
        raise ValueError("Old and new envelopes must belong to the same building")

    now = datetime.now(UTC)
    old_envelope.status = "superseded"
    old_envelope.superseded_at = now
    old_envelope.is_sovereign = False

    new_envelope.supersedes_id = old_envelope_id
    new_envelope.is_sovereign = True

    # Record canonical ritual trace
    await ritual_service.supersede(
        db,
        old_envelope.building_id,
        "passport",
        old_envelope.id,
        superseded_by_id=new_envelope.created_by_id,
        org_id=old_envelope.organization_id,
        new_target_id=new_envelope.id,
        reason=reason,
    )

    return old_envelope


async def reimport_envelope(
    db: AsyncSession,
    envelope_data: dict,
    building_id: UUID,
    imported_by_id: UUID,
    org_id: UUID,
) -> BuildingPassportEnvelope:
    """Re-import a previously exported envelope into a new building context.

    Used when a building changes hands and the new owner imports the old passport.
    The imported envelope gets a new version number but preserves original content hash.
    """
    # Verify building exists
    from app.models.building import Building

    building_result = await db.execute(select(Building).where(Building.id == building_id))
    if not building_result.scalar_one_or_none():
        raise ValueError("Building not found")

    version = await _next_version(db, building_id)

    # Extract passport_data from the envelope_data
    passport_data = envelope_data.get("passport_data", envelope_data)
    sections = envelope_data.get("sections_included", list(passport_data.keys()))
    original_hash = envelope_data.get("content_hash", _compute_hash(passport_data))

    envelope = BuildingPassportEnvelope(
        building_id=building_id,
        organization_id=org_id,
        created_by_id=imported_by_id,
        version=version,
        version_label=f"Imported from previous owner (v{envelope_data.get('version', '?')})",
        passport_data=passport_data,
        sections_included=sections,
        content_hash=original_hash,
        redaction_profile=envelope_data.get("redaction_profile", "none"),
        financials_redacted=envelope_data.get("financials_redacted", False),
        personal_data_redacted=envelope_data.get("personal_data_redacted", False),
        is_sovereign=False,  # imported envelopes are not sovereign by default
        status="frozen",  # imported envelopes are immutable
        reimportable=True,
        reimport_format="json",
    )
    db.add(envelope)
    return envelope


async def get_envelope_history(
    db: AsyncSession,
    building_id: UUID,
) -> list[BuildingPassportEnvelope]:
    """Get version history of all envelopes for a building."""
    result = await db.execute(
        select(BuildingPassportEnvelope)
        .where(BuildingPassportEnvelope.building_id == building_id)
        .order_by(BuildingPassportEnvelope.version.desc())
    )
    return list(result.scalars().all())


async def get_latest_envelope(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingPassportEnvelope | None:
    """Get the current sovereign envelope for a building."""
    result = await db.execute(
        select(BuildingPassportEnvelope)
        .where(
            and_(
                BuildingPassportEnvelope.building_id == building_id,
                BuildingPassportEnvelope.is_sovereign.is_(True),
            )
        )
        .order_by(BuildingPassportEnvelope.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_envelope(
    db: AsyncSession,
    envelope_id: UUID,
) -> BuildingPassportEnvelope | None:
    """Get a single envelope by ID."""
    result = await db.execute(select(BuildingPassportEnvelope).where(BuildingPassportEnvelope.id == envelope_id))
    return result.scalar_one_or_none()


async def _get_or_raise(db: AsyncSession, envelope_id: UUID) -> BuildingPassportEnvelope:
    """Get envelope or raise ValueError."""
    envelope = await get_envelope(db, envelope_id)
    if not envelope:
        raise ValueError("Passport envelope not found")
    return envelope
