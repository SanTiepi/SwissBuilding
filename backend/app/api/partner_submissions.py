"""BatiConnect -- Partner Submissions API.

Governed submission endpoints where partners submit data through their
exchange contracts. Every submission goes through:
1. Contract validation (access + conformance)
2. Object creation (extraction, quote, acknowledgment)
3. Audit trail (exchange event)
4. Review task creation
5. Ritual trace (where applicable)
6. Typed receipt returned
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.partner_submission import (
    PartnerAcknowledgmentSubmission,
    PartnerDiagnosticSubmission,
    PartnerQuoteSubmission,
    PendingSubmissionRead,
    SubmissionReceipt,
)
from app.services import partner_submission_service as svc

router = APIRouter()


@router.post(
    "/partner-submissions/diagnostic",
    response_model=SubmissionReceipt,
    status_code=201,
    tags=["Partner Submissions"],
)
async def submit_diagnostic_report(
    submission: PartnerDiagnosticSubmission,
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Partner submits a diagnostic report.

    Flow:
    1. Validate partner access via exchange contract
    2. Validate submission data against conformance profile
    3. Create diagnostic extraction (draft, requires review)
    4. Record exchange event for audit trail
    5. Create review task
    6. Return submission receipt
    """
    if current_user.organization_id is None:
        raise HTTPException(status_code=403, detail="User must belong to a partner organization")

    result = await svc.submit_diagnostic(
        db,
        partner_org_id=current_user.organization_id,
        building_id=submission.building_id,
        diagnostic_type=submission.diagnostic_type,
        report_reference=submission.report_reference,
        report_date=submission.report_date,
        submitted_by_id=current_user.id,
        document_id=submission.document_id,
        text_content=submission.text_content,
        metadata=submission.metadata,
    )

    if result["status"] == "rejected":
        raise HTTPException(status_code=403, detail=result["next_steps"])

    await db.commit()
    return SubmissionReceipt(
        submission_id=result["submission_id"],
        status=result["status"],
        contract_id=result["contract_id"],
        conformance_result=result.get("conformance_result"),
        timestamp=result["timestamp"],
        next_steps=result["next_steps"],
    )


@router.post(
    "/partner-submissions/quote",
    response_model=SubmissionReceipt,
    status_code=201,
    tags=["Partner Submissions"],
)
async def submit_quote(
    submission: PartnerQuoteSubmission,
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Partner submits a quote for an open tender.

    Flow:
    1. Validate partner access via exchange contract
    2. Verify tender exists
    3. Create tender quote
    4. Record exchange event for audit trail
    5. Create review task
    6. Record partner trust signal
    7. Return submission receipt
    """
    if current_user.organization_id is None:
        raise HTTPException(status_code=403, detail="User must belong to a partner organization")

    result = await svc.submit_quote(
        db,
        partner_org_id=current_user.organization_id,
        tender_id=submission.tender_id,
        total_amount_chf=submission.total_amount_chf,
        scope_description=submission.scope_description,
        validity_date=submission.validity_date,
        submitted_by_id=current_user.id,
        document_id=submission.document_id,
        metadata=submission.metadata,
    )

    if result["status"] == "rejected":
        raise HTTPException(status_code=403, detail=result["next_steps"])

    await db.commit()
    return SubmissionReceipt(
        submission_id=result["submission_id"],
        status=result["status"],
        contract_id=result["contract_id"],
        conformance_result=result.get("conformance_result"),
        timestamp=result["timestamp"],
        next_steps=result["next_steps"],
    )


@router.post(
    "/partner-submissions/acknowledgment",
    response_model=SubmissionReceipt,
    status_code=201,
    tags=["Partner Submissions"],
)
async def submit_acknowledgment(
    submission: PartnerAcknowledgmentSubmission,
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Partner acknowledges receipt of a transfer/pack.

    Flow:
    1. Validate partner access via exchange contract
    2. Record acknowledgment via TruthRitual
    3. Record exchange event for audit trail
    4. Return submission receipt
    """
    if current_user.organization_id is None:
        raise HTTPException(status_code=403, detail="User must belong to a partner organization")

    result = await svc.submit_acknowledgment(
        db,
        partner_org_id=current_user.organization_id,
        submitted_by_id=current_user.id,
        acknowledged=submission.acknowledged,
        envelope_id=submission.envelope_id,
        pack_id=submission.pack_id,
        notes=submission.notes,
    )

    if result["status"] == "rejected":
        raise HTTPException(status_code=403, detail=result["next_steps"])

    await db.commit()
    return SubmissionReceipt(
        submission_id=result["submission_id"],
        status=result["status"],
        contract_id=result["contract_id"],
        conformance_result=result.get("conformance_result"),
        timestamp=result["timestamp"],
        next_steps=result["next_steps"],
    )


@router.get(
    "/partner-submissions/pending",
    response_model=list[PendingSubmissionRead],
    tags=["Partner Submissions"],
)
async def get_pending_submissions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List pending partner submissions for review."""
    if current_user.organization_id is None:
        return []

    tasks = await svc.get_pending_submissions(
        db,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )
    return tasks
