"""BatiConnect — Marketplace Trust API routes (Award, Completion, Review)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.marketplace_trust import (
    AwardConfirmationCreate,
    AwardConfirmationRead,
    CompletionConfirmAction,
    CompletionConfirmationRead,
    RatingSummary,
    ReviewCreate,
    ReviewModerateAction,
    ReviewRead,
)
from app.services.marketplace_trust_service import (
    award_quote,
    confirm_completion_client,
    confirm_completion_company,
    get_award,
    get_company_rating_summary,
    get_company_reviews,
    get_completion,
    get_pending_reviews,
    link_to_building,
    moderate_review,
    submit_review,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Award
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/requests/{request_id}/award",
    response_model=AwardConfirmationRead,
    status_code=201,
)
async def award_quote_endpoint(
    request_id: UUID,
    payload: AwardConfirmationCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await award_quote(
            db,
            request_id=request_id,
            quote_id=payload.quote_id,
            user_id=current_user.id,
            conditions=payload.conditions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


@router.get(
    "/marketplace/awards/{award_id}",
    response_model=AwardConfirmationRead,
)
async def get_award_endpoint(
    award_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    award = await get_award(db, award_id)
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    return award


# ---------------------------------------------------------------------------
# Completion Confirmation
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/completions/{completion_id}",
    response_model=CompletionConfirmationRead,
)
async def get_completion_endpoint(
    completion_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    completion = await get_completion(db, completion_id)
    if not completion:
        raise HTTPException(status_code=404, detail="Completion confirmation not found")
    return completion


@router.post(
    "/marketplace/completions/{completion_id}/confirm-client",
    response_model=CompletionConfirmationRead,
)
async def confirm_client_endpoint(
    completion_id: UUID,
    payload: CompletionConfirmAction | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    notes = payload.notes if payload else None
    try:
        result = await confirm_completion_client(db, completion_id, current_user.id, notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


@router.post(
    "/marketplace/completions/{completion_id}/confirm-company",
    response_model=CompletionConfirmationRead,
)
async def confirm_company_endpoint(
    completion_id: UUID,
    payload: CompletionConfirmAction | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    notes = payload.notes if payload else None
    try:
        result = await confirm_completion_company(db, completion_id, current_user.id, notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/reviews",
    response_model=ReviewRead,
    status_code=201,
)
async def submit_review_endpoint(
    payload: ReviewCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    try:
        result = await submit_review(db, data, reviewer_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


@router.get(
    "/marketplace/companies/{company_id}/reviews",
    response_model=list[ReviewRead],
)
async def get_company_reviews_endpoint(
    company_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await get_company_reviews(db, company_id)


@router.get(
    "/marketplace/reviews/pending",
    response_model=list[ReviewRead],
)
async def get_pending_reviews_endpoint(
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    return await get_pending_reviews(db)


@router.post(
    "/marketplace/reviews/{review_id}/moderate",
    response_model=ReviewRead,
)
async def moderate_review_endpoint(
    review_id: UUID,
    payload: ReviewModerateAction,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await moderate_review(
            db,
            review_id=review_id,
            moderator_user_id=current_user.id,
            decision=payload.decision,
            notes=payload.notes,
            rejection_reason=payload.rejection_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Rating Summary
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/companies/{company_id}/rating-summary",
    response_model=RatingSummary,
)
async def rating_summary_endpoint(
    company_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await get_company_rating_summary(db, company_id)


# ---------------------------------------------------------------------------
# Building Linkage
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/awards/{award_id}/link-building",
)
async def link_building_endpoint(
    award_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await link_to_building(db, award_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return result
