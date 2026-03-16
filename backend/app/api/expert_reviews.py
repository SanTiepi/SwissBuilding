"""Expert review governance API — submit, list, withdraw, query overrides."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.expert_review import ExpertReviewCreate, ExpertReviewList, ExpertReviewRead
from app.services.expert_review_service import (
    create_review,
    get_active_overrides,
    get_review,
    list_reviews,
    withdraw_review,
)

router = APIRouter()


@router.post(
    "/expert-reviews",
    response_model=ExpertReviewRead,
    status_code=201,
)
async def create_expert_review(
    data: ExpertReviewCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Submit an expert review on an automated finding."""
    review = await create_review(
        db,
        data=data,
        reviewed_by=current_user.id,
        reviewer_role=current_user.role,
    )
    return review


@router.get(
    "/expert-reviews",
    response_model=ExpertReviewList,
)
async def list_expert_reviews(
    building_id: UUID | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List expert reviews with optional filters."""
    offset = (page - 1) * size
    items, total = await list_reviews(
        db,
        building_id=building_id,
        target_type=target_type,
        target_id=target_id,
        limit=size,
        offset=offset,
    )
    return {"items": items, "total": total}


@router.get(
    "/expert-reviews/{review_id}",
    response_model=ExpertReviewRead,
)
async def get_expert_review(
    review_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single expert review."""
    review = await get_review(db, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Expert review not found")
    return review


@router.delete(
    "/expert-reviews/{review_id}",
    response_model=ExpertReviewRead,
)
async def withdraw_expert_review(
    review_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw an expert review (only the original reviewer can do this)."""
    review = await withdraw_review(db, review_id, current_user.id)
    if review is None:
        raise HTTPException(status_code=404, detail="Expert review not found or not authorized")
    return review


@router.get(
    "/buildings/{building_id}/expert-overrides",
    response_model=list[ExpertReviewRead],
)
async def get_building_expert_overrides(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all active expert overrides for a building."""
    return await get_active_overrides(db, building_id)
