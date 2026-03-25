"""BatiConnect — Exchange Hardening + Contributor Gateway API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.exchange import ImportReceiptRead
from app.schemas.exchange_hardening import (
    ContributorReceiptRead,
    ContributorRequestCreate,
    ContributorRequestRead,
    ContributorSubmissionCreate,
    ContributorSubmissionRead,
    DeliveryAttemptRead,
    ExchangeValidationReportRead,
    ImportReviewRequest,
    PassportStateDiffRead,
    RelianceSignalCreate,
    RelianceSignalRead,
    SubmissionRejectRequest,
    WebhookSubscriptionCreate,
    WebhookSubscriptionRead,
)
from app.services.contributor_gateway_service import (
    accept_submission,
    create_request,
    list_pending_submissions,
    list_requests,
    reject_submission,
    submit,
)
from app.services.exchange_hardening_service import (
    compute_publication_diff,
    integrate_import,
    record_reliance_signal,
    review_import,
    validate_import,
)
from app.services.partner_webhook_service import (
    create_subscription,
    delete_subscription,
    get_delivery_history,
    list_subscriptions,
)

router = APIRouter()


# --- Publication Diff ---


@router.get(
    "/publications/{publication_id}/diff",
    response_model=PassportStateDiffRead,
)
async def get_publication_diff(
    publication_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        diff = await compute_publication_diff(db, publication_id)
        await db.commit()
        return diff
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


# --- Import Validation ---


@router.post(
    "/import-receipts/{receipt_id}/validate",
    response_model=ExchangeValidationReportRead,
)
async def validate_import_endpoint(
    receipt_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        report = await validate_import(db, receipt_id)
        await db.commit()
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post(
    "/import-receipts/{receipt_id}/review",
    response_model=ImportReceiptRead,
)
async def review_import_endpoint(
    receipt_id: UUID,
    payload: ImportReviewRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        receipt = await review_import(db, receipt_id, current_user.id, payload.decision)
        await db.commit()
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post(
    "/import-receipts/{receipt_id}/integrate",
    response_model=ImportReceiptRead,
)
async def integrate_import_endpoint(
    receipt_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        receipt = await integrate_import(db, receipt_id, current_user.id)
        await db.commit()
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


# --- Reliance Signals ---


@router.post(
    "/reliance-signals",
    response_model=RelianceSignalRead,
    status_code=201,
)
async def create_reliance_signal(
    payload: RelianceSignalCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    signal = await record_reliance_signal(db, data)
    await db.commit()
    return signal


# --- Partner Webhooks ---


@router.post(
    "/partner-webhooks",
    response_model=WebhookSubscriptionRead,
    status_code=201,
)
async def create_webhook(
    payload: WebhookSubscriptionCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    sub = await create_subscription(db, data)
    await db.commit()
    return sub


@router.get(
    "/partner-webhooks",
    response_model=list[WebhookSubscriptionRead],
)
async def list_webhooks(
    org_id: UUID | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_subscriptions(db, org_id)


@router.delete("/partner-webhooks/{sub_id}", status_code=204)
async def delete_webhook(
    sub_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_subscription(db, sub_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    await db.commit()


@router.get(
    "/partner-webhooks/{sub_id}/deliveries",
    response_model=list[DeliveryAttemptRead],
)
async def list_deliveries(
    sub_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await get_delivery_history(db, sub_id)


# --- Contributor Gateway ---


@router.post(
    "/contributor-requests",
    response_model=ContributorRequestRead,
    status_code=201,
)
async def create_contributor_request(
    payload: ContributorRequestCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    req = await create_request(
        db,
        building_id=payload.building_id,
        contributor_type=payload.contributor_type,
        created_by_user_id=current_user.id,
        scope_description=payload.scope_description,
        expires_in_hours=payload.expires_in_hours,
        linked_procedure_id=payload.linked_procedure_id,
        linked_remediation_id=payload.linked_remediation_id,
    )
    await db.commit()
    return req


@router.get(
    "/contributor-requests",
    response_model=list[ContributorRequestRead],
)
async def list_contributor_requests(
    building_id: UUID | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_requests(db, building_id)


@router.post(
    "/contributor-submit/{token}",
    response_model=ContributorSubmissionRead,
    status_code=201,
)
async def contributor_submit(
    token: str,
    payload: ContributorSubmissionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Bounded endpoint — no full auth required, token-based access."""
    try:
        data = payload.model_dump(exclude_unset=True)
        sub = await submit(db, token, data)
        await db.commit()
        return sub
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from None


@router.get(
    "/contributor-submissions/pending",
    response_model=list[ContributorSubmissionRead],
)
async def list_pending(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_pending_submissions(db)


@router.post(
    "/contributor-submissions/{submission_id}/accept",
    response_model=ContributorReceiptRead,
)
async def accept_contributor_submission(
    submission_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        receipt = await accept_submission(db, submission_id, current_user.id)
        await db.commit()
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post(
    "/contributor-submissions/{submission_id}/reject",
    response_model=ContributorSubmissionRead,
)
async def reject_contributor_submission(
    submission_id: UUID,
    payload: SubmissionRejectRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    try:
        sub = await reject_submission(db, submission_id, current_user.id, payload.notes)
        await db.commit()
        return sub
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
