"""Post-works truth tracker API — contractor completion, status, certificates."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.post_work_item import PostWorkItem
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.post_work_item import (
    CompletionStatusRead,
    PostWorkItemComplete,
    PostWorkItemCreate,
    PostWorkItemRead,
    WorksCompletionCertificateRead,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_item_or_404(db: AsyncSession, building_id: UUID, item_id: UUID) -> PostWorkItem:
    result = await db.execute(
        select(PostWorkItem).where(
            PostWorkItem.id == item_id,
            PostWorkItem.building_id == building_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Post-work item not found")
    return item


@router.get(
    "/buildings/{building_id}/post-work-items",
    response_model=PaginatedResponse[PostWorkItemRead],
)
async def list_post_work_items_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List post-work items for a building."""
    await _get_building_or_404(db, building_id)
    from app.services.post_works_tracker_service import list_post_work_items

    return await list_post_work_items(db, building_id, status=status, page=page, size=size)


@router.post(
    "/buildings/{building_id}/post-work-items",
    response_model=PostWorkItemRead,
    status_code=201,
)
async def create_post_work_item_endpoint(
    building_id: UUID,
    data: PostWorkItemCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new post-work item to track."""
    await _get_building_or_404(db, building_id)
    from app.services.post_works_tracker_service import create_post_work_item

    return await create_post_work_item(db, building_id, current_user.id, data.model_dump())


@router.post(
    "/buildings/{building_id}/post-work-items/{item_id}/complete",
    response_model=PostWorkItemRead,
)
async def complete_post_work_item_endpoint(
    building_id: UUID,
    item_id: UUID,
    data: PostWorkItemComplete,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Contractor submits completion with photo evidence."""
    await _get_building_or_404(db, building_id)
    item = await _get_item_or_404(db, building_id, item_id)

    if item.contractor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only assigned contractor can complete this item")

    from app.services.post_works_tracker_service import complete_post_work_item

    return await complete_post_work_item(
        db,
        item,
        data.photo_uris,
        before_after_pairs=data.before_after_pairs,
        notes=data.notes,
    )


@router.get(
    "/buildings/{building_id}/completion-status",
    response_model=CompletionStatusRead,
)
async def get_completion_status_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get overall completion % and breakdown for a building."""
    await _get_building_or_404(db, building_id)
    from app.services.post_works_tracker_service import get_completion_status

    return await get_completion_status(db, building_id)


@router.get(
    "/buildings/{building_id}/completion-certificate",
    response_model=WorksCompletionCertificateRead,
)
async def get_completion_certificate_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get or generate completion certificate (only if 100% complete)."""
    await _get_building_or_404(db, building_id)
    from app.services.post_works_tracker_service import get_or_create_certificate

    cert = await get_or_create_certificate(db, building_id)
    if not cert:
        raise HTTPException(status_code=409, detail="Not all items are completed — certificate cannot be issued")
    return cert
