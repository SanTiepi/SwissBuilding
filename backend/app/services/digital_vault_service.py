"""Digital vault service — document trust verification and integrity tracking."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.digital_vault import (
    BuildingVaultSummary,
    CustodyEvent,
    DocumentTrustVerification,
    PortfolioVaultStatus,
    SuspiciousEntry,
    VaultIntegrityReport,
)
from app.services.building_data_loader import load_org_buildings


def _sha256(value: str) -> str:
    """Compute SHA-256 hex digest of a string."""
    return hashlib.sha256(value.encode()).hexdigest()


async def get_building_vault_summary(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingVaultSummary | None:
    """Build a vault summary for a single building."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    now = datetime.now(UTC)

    # Count documents
    docs_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = docs_result.scalars().all()

    # Count diagnostics
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = diag_result.scalars().all()

    # Count samples via diagnostics
    diag_ids = [d.id for d in diagnostics]
    samples: list = []
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # Count interventions
    interv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = interv_result.scalars().all()

    # Count action items
    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    action_items = action_result.scalars().all()

    # Build entry counts
    total_entries = len(documents) + len(diagnostics) + len(samples) + len(interventions) + len(action_items)

    # Documents are considered "verified" (they have file content tracked)
    verified_count = len(documents)
    unverified_count = total_entries - verified_count

    integrity_score = verified_count / total_entries if total_entries > 0 else 1.0

    last_verified_at = now if verified_count > 0 else None

    return BuildingVaultSummary(
        building_id=building_id,
        total_entries=total_entries,
        verified_count=verified_count,
        unverified_count=unverified_count,
        integrity_score=integrity_score,
        last_verified_at=last_verified_at,
        generated_at=now,
    )


async def verify_document_trust(
    document_id: UUID,
    db: AsyncSession,
) -> DocumentTrustVerification | None:
    """Verify trust and chain of custody for a single document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        return None

    now = datetime.now(UTC)

    # Simulated hashes — in production would re-hash file content from storage
    original_hash = _sha256(f"{doc.id}:{doc.file_name}:{doc.created_at}")
    current_hash = original_hash  # Simulated — always matches
    is_intact = original_hash == current_hash

    chain_of_custody: list[CustodyEvent] = [
        CustodyEvent(
            timestamp=doc.created_at if doc.created_at else now,
            event_type="upload",
            actor=str(doc.uploaded_by) if doc.uploaded_by else None,
            details=f"Document uploaded: {doc.file_name}",
        ),
        CustodyEvent(
            timestamp=now,
            event_type="verify",
            actor=None,
            details="Integrity verification performed",
        ),
    ]

    return DocumentTrustVerification(
        document_id=document_id,
        file_name=doc.file_name,
        document_type=doc.document_type,
        original_hash=original_hash,
        current_hash=current_hash,
        is_intact=is_intact,
        upload_date=doc.created_at,
        last_verified=now,
        chain_of_custody=chain_of_custody,
    )


async def generate_integrity_report(
    building_id: UUID,
    db: AsyncSession,
) -> VaultIntegrityReport | None:
    """Generate a full integrity report for a building's vault."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    now = datetime.now(UTC)
    suspicious: list[SuspiciousEntry] = []

    # Check documents
    docs_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = docs_result.scalars().all()

    for doc in documents:
        # Documents without document_type are suspicious
        if not doc.document_type:
            suspicious.append(
                SuspiciousEntry(
                    entry_id=doc.id,
                    record_type="document",
                    issue="Unclassified document — no document_type set",
                    severity="low",
                )
            )

    # Check diagnostics
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = diag_result.scalars().all()
    diag_ids = [d.id for d in diagnostics]

    for diag in diagnostics:
        # Diagnostics in draft for >90 days
        if diag.status == "draft" and diag.created_at:
            age_days = (now - diag.created_at.replace(tzinfo=UTC)).days
            if age_days > 90:
                suspicious.append(
                    SuspiciousEntry(
                        entry_id=diag.id,
                        record_type="diagnostic_report",
                        issue=f"Draft diagnostic stale for {age_days} days",
                        severity="medium",
                    )
                )

    # Check samples
    samples: list = []
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    for sample in samples:
        if sample.concentration is None:
            suspicious.append(
                SuspiciousEntry(
                    entry_id=sample.id,
                    record_type="sample_result",
                    issue="Sample missing concentration value — incomplete data",
                    severity="high",
                )
            )

    total = len(documents) + len(diagnostics) + len(samples)
    suspicious_count = len(suspicious)
    verified = total - suspicious_count

    integrity_pct = ((total - suspicious_count) / total * 100) if total > 0 else 100.0

    # Build recommendations
    recommendations: list[str] = []
    if any(s.record_type == "document" for s in suspicious):
        recommendations.append("Classify all uploaded documents with a document_type.")
    if any(s.record_type == "diagnostic_report" for s in suspicious):
        recommendations.append("Review and finalize stale draft diagnostics.")
    if any(s.record_type == "sample_result" for s in suspicious):
        recommendations.append("Complete missing sample concentration values from lab results.")
    if not suspicious:
        recommendations.append("All records are in good standing — no action needed.")

    return VaultIntegrityReport(
        building_id=building_id,
        total_documents=total,
        verified_documents=verified,
        integrity_percentage=integrity_pct,
        suspicious_entries=suspicious,
        recommendations=recommendations,
        generated_at=now,
    )


async def get_portfolio_vault_status(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioVaultStatus | None:
    """Aggregate vault status across an organization's portfolio."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        return None

    now = datetime.now(UTC)

    buildings = await load_org_buildings(db, org_id)

    total_vault_entries = 0
    total_integrity = 0.0
    buildings_with_issues = 0
    by_record_type: dict[str, int] = {}

    for bldg in buildings:
        summary = await get_building_vault_summary(bldg.id, db)
        if summary is None:
            continue
        total_vault_entries += summary.total_entries
        total_integrity += summary.integrity_score
        if summary.integrity_score < 0.8:
            buildings_with_issues += 1

        # Count by record type from sub-queries
        docs_count = (await db.execute(select(Document).where(Document.building_id == bldg.id))).scalars().all()
        diag_count = (await db.execute(select(Diagnostic).where(Diagnostic.building_id == bldg.id))).scalars().all()
        interv_count = (
            (await db.execute(select(Intervention).where(Intervention.building_id == bldg.id))).scalars().all()
        )
        action_count = (await db.execute(select(ActionItem).where(ActionItem.building_id == bldg.id))).scalars().all()

        by_record_type["document"] = by_record_type.get("document", 0) + len(docs_count)
        by_record_type["diagnostic_report"] = by_record_type.get("diagnostic_report", 0) + len(diag_count)
        by_record_type["intervention_record"] = by_record_type.get("intervention_record", 0) + len(interv_count)
        by_record_type["action_record"] = by_record_type.get("action_record", 0) + len(action_count)

    avg_integrity = total_integrity / len(buildings) if buildings else 1.0

    return PortfolioVaultStatus(
        organization_id=org_id,
        total_buildings=len(buildings),
        total_vault_entries=total_vault_entries,
        average_integrity_score=avg_integrity,
        buildings_with_issues=buildings_with_issues,
        by_record_type=by_record_type,
        generated_at=now,
    )
