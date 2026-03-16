from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.compliance_artefact import ComplianceArtefactCreate


async def create_artefact(
    db: AsyncSession,
    building_id: UUID,
    data: ComplianceArtefactCreate,
    created_by: UUID,
) -> ComplianceArtefact:
    artefact = ComplianceArtefact(
        building_id=building_id,
        created_by=created_by,
        **data.model_dump(),
    )
    db.add(artefact)
    await db.flush()
    return artefact


async def submit_artefact(db: AsyncSession, artefact_id: UUID) -> ComplianceArtefact:
    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.id == artefact_id))
    artefact = result.scalar_one_or_none()
    if artefact is None:
        raise ValueError("Artefact not found")
    if artefact.status != "draft":
        raise ValueError(f"Cannot submit artefact with status '{artefact.status}', must be 'draft'")
    artefact.status = "submitted"
    artefact.submitted_at = datetime.now(UTC)
    await db.flush()
    return artefact


async def acknowledge_artefact(
    db: AsyncSession,
    artefact_id: UUID,
    reference_number: str | None = None,
) -> ComplianceArtefact:
    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.id == artefact_id))
    artefact = result.scalar_one_or_none()
    if artefact is None:
        raise ValueError("Artefact not found")
    if artefact.status != "submitted":
        raise ValueError(f"Cannot acknowledge artefact with status '{artefact.status}', must be 'submitted'")
    artefact.status = "acknowledged"
    artefact.acknowledged_at = datetime.now(UTC)
    if reference_number is not None:
        artefact.reference_number = reference_number
    await db.flush()
    return artefact


async def reject_artefact(
    db: AsyncSession,
    artefact_id: UUID,
    reason: str | None = None,
) -> ComplianceArtefact:
    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.id == artefact_id))
    artefact = result.scalar_one_or_none()
    if artefact is None:
        raise ValueError("Artefact not found")
    if artefact.status != "submitted":
        raise ValueError(f"Cannot reject artefact with status '{artefact.status}', must be 'submitted'")
    artefact.status = "rejected"
    if reason is not None:
        artefact.description = (artefact.description or "") + f"\n[Rejection reason]: {reason}"
    await db.flush()
    return artefact


async def get_building_compliance_summary(db: AsyncSession, building_id: UUID) -> dict:
    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = result.scalars().all()

    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    pending_submissions = 0
    expired = 0
    now = datetime.now(UTC)

    for a in artefacts:
        by_type[a.artefact_type] = by_type.get(a.artefact_type, 0) + 1
        by_status[a.status] = by_status.get(a.status, 0) + 1
        if a.status == "draft":
            pending_submissions += 1
        if a.expires_at and a.expires_at.replace(tzinfo=UTC) < now:
            expired += 1

    return {
        "total": len(artefacts),
        "by_type": by_type,
        "by_status": by_status,
        "pending_submissions": pending_submissions,
        "expired": expired,
    }


async def check_required_artefacts(db: AsyncSession, building_id: UUID) -> list[dict]:
    missing: list[dict] = []

    # Check if building has positive asbestos samples → needs suva_notification
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = diag_result.scalars().all()
    diag_ids = [d.id for d in diagnostics]

    has_positive_asbestos = False
    if diag_ids:
        sample_result = await db.execute(
            select(Sample).where(
                Sample.diagnostic_id.in_(diag_ids),
                Sample.pollutant_type == "asbestos",
                Sample.threshold_exceeded.is_(True),
            )
        )
        if sample_result.scalars().first() is not None:
            has_positive_asbestos = True

    if has_positive_asbestos:
        # Check if suva_notification exists
        suva_result = await db.execute(
            select(func.count())
            .select_from(ComplianceArtefact)
            .where(
                ComplianceArtefact.building_id == building_id,
                ComplianceArtefact.artefact_type == "suva_notification",
            )
        )
        if (suva_result.scalar() or 0) == 0:
            missing.append(
                {
                    "artefact_type": "suva_notification",
                    "reason": "Building has positive asbestos samples — SUVA notification required",
                    "legal_basis": "OTConst Art. 82-86",
                }
            )

    # Check if completed interventions exist → needs post_remediation_report
    intervention_result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status == "completed",
        )
    )
    completed_interventions = intervention_result.scalars().all()

    if completed_interventions:
        report_result = await db.execute(
            select(func.count())
            .select_from(ComplianceArtefact)
            .where(
                ComplianceArtefact.building_id == building_id,
                ComplianceArtefact.artefact_type == "post_remediation_report",
            )
        )
        if (report_result.scalar() or 0) == 0:
            missing.append(
                {
                    "artefact_type": "post_remediation_report",
                    "reason": "Building has completed interventions — post-remediation report required",
                }
            )

    return missing
