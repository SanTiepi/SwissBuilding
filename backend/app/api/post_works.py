"""Post-works state management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.post_works_state import PostWorksState
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.post_works import (
    PostWorksStateCreate,
    PostWorksStateRead,
    PostWorksStateUpdate,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_state_or_404(db: AsyncSession, building_id: UUID, state_id: UUID) -> PostWorksState:
    result = await db.execute(
        select(PostWorksState).where(
            PostWorksState.id == state_id,
            PostWorksState.building_id == building_id,
        )
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="Post-works state not found")
    return state


@router.get(
    "/buildings/{building_id}/post-works",
    response_model=PaginatedResponse[PostWorksStateRead],
)
async def list_post_works_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    state_type: str | None = None,
    pollutant_type: str | None = None,
    current_user: User = Depends(require_permission("post_works", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List post-works states for a building."""
    await _get_building_or_404(db, building_id)

    query = select(PostWorksState).where(PostWorksState.building_id == building_id)
    count_query = select(func.count()).select_from(PostWorksState).where(PostWorksState.building_id == building_id)

    if state_type:
        query = query.where(PostWorksState.state_type == state_type)
        count_query = count_query.where(PostWorksState.state_type == state_type)
    if pollutant_type:
        query = query.where(PostWorksState.pollutant_type == pollutant_type)
        count_query = count_query.where(PostWorksState.pollutant_type == pollutant_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(PostWorksState.recorded_at.desc()).offset((page - 1) * size).limit(size)
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


@router.get(
    "/buildings/{building_id}/post-works/compare",
)
async def compare_post_works_endpoint(
    building_id: UUID,
    intervention_id: UUID | None = None,
    current_user: User = Depends(require_permission("post_works", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare before/after state for a building."""
    await _get_building_or_404(db, building_id)
    from app.services.post_works_service import compare_before_after

    return await compare_before_after(db, building_id, intervention_id)


@router.get(
    "/buildings/{building_id}/post-works/summary",
)
async def post_works_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("post_works", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated summary of post-works states for a building."""
    await _get_building_or_404(db, building_id)
    from app.services.post_works_service import get_post_works_summary

    return await get_post_works_summary(db, building_id)


@router.post(
    "/buildings/{building_id}/post-works",
    response_model=PostWorksStateRead,
    status_code=201,
)
async def create_post_works_endpoint(
    building_id: UUID,
    data: PostWorksStateCreate,
    current_user: User = Depends(require_permission("post_works", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new post-works state."""
    await _get_building_or_404(db, building_id)

    state = PostWorksState(
        building_id=building_id,
        recorded_by=current_user.id,
        **data.model_dump(),
    )
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return state


@router.get(
    "/buildings/{building_id}/post-works/{state_id}",
    response_model=PostWorksStateRead,
)
async def get_post_works_endpoint(
    building_id: UUID,
    state_id: UUID,
    current_user: User = Depends(require_permission("post_works", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single post-works state."""
    await _get_building_or_404(db, building_id)
    return await _get_state_or_404(db, building_id, state_id)


@router.put(
    "/buildings/{building_id}/post-works/{state_id}",
    response_model=PostWorksStateRead,
)
async def update_post_works_endpoint(
    building_id: UUID,
    state_id: UUID,
    data: PostWorksStateUpdate,
    current_user: User = Depends(require_permission("post_works", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a post-works state."""
    await _get_building_or_404(db, building_id)
    state = await _get_state_or_404(db, building_id, state_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(state, key, value)

    await db.commit()
    await db.refresh(state)
    return state


@router.delete(
    "/buildings/{building_id}/post-works/{state_id}",
    status_code=204,
)
async def delete_post_works_endpoint(
    building_id: UUID,
    state_id: UUID,
    current_user: User = Depends(require_permission("post_works", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a post-works state."""
    await _get_building_or_404(db, building_id)
    state = await _get_state_or_404(db, building_id, state_id)
    await db.delete(state)
    await db.commit()
