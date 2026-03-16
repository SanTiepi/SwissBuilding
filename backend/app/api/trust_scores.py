"""Building trust score management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.trust_score import (
    BuildingTrustScoreCreate,
    BuildingTrustScoreRead,
    BuildingTrustScoreUpdate,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_score_or_404(db: AsyncSession, building_id: UUID, score_id: UUID) -> BuildingTrustScore:
    result = await db.execute(
        select(BuildingTrustScore).where(
            BuildingTrustScore.id == score_id,
            BuildingTrustScore.building_id == building_id,
        )
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Building trust score not found")
    return score


@router.get(
    "/buildings/{building_id}/trust-scores",
    response_model=PaginatedResponse[BuildingTrustScoreRead],
)
async def list_trust_scores_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    trend: str | None = None,
    assessed_by: str | None = None,
    current_user: User = Depends(require_permission("trust_scores", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List trust scores for a building."""
    await _get_building_or_404(db, building_id)

    query = select(BuildingTrustScore).where(BuildingTrustScore.building_id == building_id)
    count_query = (
        select(func.count()).select_from(BuildingTrustScore).where(BuildingTrustScore.building_id == building_id)
    )

    if trend:
        query = query.where(BuildingTrustScore.trend == trend)
        count_query = count_query.where(BuildingTrustScore.trend == trend)
    if assessed_by:
        query = query.where(BuildingTrustScore.assessed_by == assessed_by)
        count_query = count_query.where(BuildingTrustScore.assessed_by == assessed_by)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(BuildingTrustScore.assessed_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post(
    "/buildings/{building_id}/trust-scores",
    response_model=BuildingTrustScoreRead,
    status_code=201,
)
async def create_trust_score_endpoint(
    building_id: UUID,
    data: BuildingTrustScoreCreate,
    current_user: User = Depends(require_permission("trust_scores", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new building trust score."""
    await _get_building_or_404(db, building_id)

    score = BuildingTrustScore(
        building_id=building_id,
        **data.model_dump(),
    )
    db.add(score)
    await db.commit()
    await db.refresh(score)
    return score


@router.get(
    "/buildings/{building_id}/trust-scores/{score_id}",
    response_model=BuildingTrustScoreRead,
)
async def get_trust_score_endpoint(
    building_id: UUID,
    score_id: UUID,
    current_user: User = Depends(require_permission("trust_scores", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single building trust score."""
    await _get_building_or_404(db, building_id)
    return await _get_score_or_404(db, building_id, score_id)


@router.put(
    "/buildings/{building_id}/trust-scores/{score_id}",
    response_model=BuildingTrustScoreRead,
)
async def update_trust_score_endpoint(
    building_id: UUID,
    score_id: UUID,
    data: BuildingTrustScoreUpdate,
    current_user: User = Depends(require_permission("trust_scores", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a building trust score."""
    await _get_building_or_404(db, building_id)
    score = await _get_score_or_404(db, building_id, score_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(score, key, value)

    await db.commit()
    await db.refresh(score)
    return score


@router.delete(
    "/buildings/{building_id}/trust-scores/{score_id}",
    status_code=204,
)
async def delete_trust_score_endpoint(
    building_id: UUID,
    score_id: UUID,
    current_user: User = Depends(require_permission("trust_scores", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a building trust score."""
    await _get_building_or_404(db, building_id)
    score = await _get_score_or_404(db, building_id, score_id)
    await db.delete(score)
    await db.commit()
