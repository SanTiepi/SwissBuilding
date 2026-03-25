"""BatiConnect — Exchange Hardening service.

Publication diff computation, import validation, reliance signal tracking.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_validation import ExchangeValidationReport, ExternalRelianceSignal
from app.models.import_receipt import PassportImportReceipt
from app.models.passport_publication import PassportPublication
from app.models.passport_state_diff import PassportStateDiff


async def compute_publication_diff(db: AsyncSession, publication_id: UUID) -> PassportStateDiff:
    """Find prior publication for same building+contract and compute diff."""
    pub = await db.get(PassportPublication, publication_id)
    if not pub:
        raise ValueError("Publication not found")

    # Find prior publication for same building + contract
    prior_q = (
        select(PassportPublication)
        .where(
            PassportPublication.building_id == pub.building_id,
            PassportPublication.contract_version_id == pub.contract_version_id,
            PassportPublication.id != pub.id,
            PassportPublication.published_at < pub.published_at,
        )
        .order_by(PassportPublication.published_at.desc())
        .limit(1)
    )
    prior_result = await db.execute(prior_q)
    prior = prior_result.scalar_one_or_none()

    # Compute diff summary
    if prior is None:
        diff_summary = {
            "added_sections": ["initial_publication"],
            "removed_sections": [],
            "changed_sections": [],
        }
        sections_changed = 1
    else:
        # Compare content hashes to detect changes
        changed = pub.content_hash != prior.content_hash
        diff_summary = {
            "added_sections": [],
            "removed_sections": [],
            "changed_sections": (
                [
                    {
                        "section": "content",
                        "field": "content_hash",
                        "old": prior.content_hash[:16],
                        "new": pub.content_hash[:16],
                    }
                ]
                if changed
                else []
            ),
        }
        sections_changed = 1 if changed else 0

    diff = PassportStateDiff(
        publication_id=publication_id,
        prior_publication_id=prior.id if prior else None,
        diff_summary=diff_summary,
        sections_changed_count=sections_changed,
        computed_at=datetime.now(UTC),
    )
    db.add(diff)
    await db.flush()
    await db.refresh(diff)
    return diff


async def validate_import(db: AsyncSession, receipt_id: UUID) -> ExchangeValidationReport:
    """Run schema/contract/version/hash/identity checks on import receipt."""
    receipt = await db.get(PassportImportReceipt, receipt_id)
    if not receipt:
        raise ValueError("Import receipt not found")

    errors: list[dict] = []

    # Schema validation: check required fields present
    schema_valid = bool(receipt.source_system and receipt.contract_code)
    if not schema_valid:
        errors.append({"check": "schema", "message": "Missing source_system or contract_code", "severity": "error"})

    # Contract validation: contract_code format
    contract_valid = len(receipt.contract_code) >= 2
    if not contract_valid:
        errors.append({"check": "contract", "message": "Contract code too short", "severity": "error"})

    # Version validation: positive version number
    version_valid = receipt.contract_version > 0
    if not version_valid:
        errors.append({"check": "version", "message": "Invalid contract version", "severity": "error"})

    # Hash validation: SHA-256 format (64 hex chars)
    hash_valid = len(receipt.content_hash) == 64 and all(c in "0123456789abcdef" for c in receipt.content_hash.lower())
    if not hash_valid:
        errors.append({"check": "hash", "message": "Invalid content hash format", "severity": "error"})

    # Identity safety: building match is unambiguous
    identity_safe = receipt.building_id is not None
    if not identity_safe:
        errors.append({"check": "identity", "message": "No building_id — match ambiguous", "severity": "warning"})

    all_pass = schema_valid and contract_valid and version_valid and hash_valid
    overall = "passed" if all_pass else ("review_required" if identity_safe else "failed")

    report = ExchangeValidationReport(
        import_receipt_id=receipt_id,
        schema_valid=schema_valid,
        contract_valid=contract_valid,
        version_valid=version_valid,
        hash_valid=hash_valid,
        identity_safe=identity_safe,
        validation_errors=errors if errors else None,
        overall_status=overall,
        validated_at=datetime.now(UTC),
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def review_import(db: AsyncSession, receipt_id: UUID, user_id: UUID, decision: str) -> PassportImportReceipt:
    """Update import receipt status after manual review."""
    receipt = await db.get(PassportImportReceipt, receipt_id)
    if not receipt:
        raise ValueError("Import receipt not found")

    valid_decisions = {"validated", "rejected", "review_required"}
    if decision not in valid_decisions:
        raise ValueError(f"Decision must be one of {valid_decisions}")

    receipt.status = decision
    if decision == "rejected":
        receipt.rejection_reason = receipt.rejection_reason or "Rejected during review"

    await db.flush()
    await db.refresh(receipt)
    return receipt


async def integrate_import(db: AsyncSession, receipt_id: UUID, user_id: UUID) -> PassportImportReceipt:
    """Mark import as integrated (only after validation passed)."""
    receipt = await db.get(PassportImportReceipt, receipt_id)
    if not receipt:
        raise ValueError("Import receipt not found")

    if receipt.status != "validated":
        raise ValueError("Can only integrate validated imports")

    receipt.status = "integrated"
    await db.flush()
    await db.refresh(receipt)
    return receipt


async def record_reliance_signal(db: AsyncSession, data: dict) -> ExternalRelianceSignal:
    """Track external consumption/acknowledgement."""
    signal = ExternalRelianceSignal(**data, recorded_at=datetime.now(UTC))
    db.add(signal)
    await db.flush()
    await db.refresh(signal)
    return signal
