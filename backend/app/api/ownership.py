"""BatiConnect — Ownership Ops API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.ownership_record import OwnershipRecord
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.ownership import (
    OwnershipRecordCreate,
    OwnershipRecordListRead,
    OwnershipRecordRead,
    OwnershipRecordUpdate,
)
from app.schemas.ownership_summary import OwnershipOpsSummary
from app.services.ownership_service import (
    create_ownership_record,
    enrich_ownership,
    enrich_ownerships,
    get_ownership_record,
    get_ownership_summary,
    list_ownership_records,
    update_ownership_record,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_record_or_404(db: AsyncSession, record_id: UUID) -> OwnershipRecord:
    record = await get_ownership_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Ownership record not found")
    return record


@router.get(
    "/buildings/{building_id}/ownership",
    response_model=PaginatedResponse[OwnershipRecordListRead],
)
async def list_ownership_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(require_permission("ownership", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    items, total = await list_ownership_records(db, building_id, page=page, size=size, status=status)
    pages = (total + size - 1) // size if total > 0 else 0
    enriched = await enrich_ownerships(db, items)
    return {"items": enriched, "total": total, "page": page, "size": size, "pages": pages}


@router.post(
    "/buildings/{building_id}/ownership",
    response_model=OwnershipRecordRead,
    status_code=201,
)
async def create_ownership_endpoint(
    building_id: UUID,
    payload: OwnershipRecordCreate,
    current_user: User = Depends(require_permission("ownership", "create")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    data.pop("building_id", None)  # use path param
    record = await create_ownership_record(db, building_id, data, created_by=current_user.id)
    await db.commit()
    return await enrich_ownership(db, record)


@router.get(
    "/ownership/{record_id}",
    response_model=OwnershipRecordRead,
)
async def get_ownership_endpoint(
    record_id: UUID,
    current_user: User = Depends(require_permission("ownership", "read")),
    db: AsyncSession = Depends(get_db),
):
    record = await _get_record_or_404(db, record_id)
    return await enrich_ownership(db, record)


@router.put(
    "/ownership/{record_id}",
    response_model=OwnershipRecordRead,
)
async def update_ownership_endpoint(
    record_id: UUID,
    payload: OwnershipRecordUpdate,
    current_user: User = Depends(require_permission("ownership", "update")),
    db: AsyncSession = Depends(get_db),
):
    record = await _get_record_or_404(db, record_id)
    data = payload.model_dump(exclude_unset=True)
    updated = await update_ownership_record(db, record, data)
    await db.commit()
    return await enrich_ownership(db, updated)


@router.get(
    "/buildings/{building_id}/ownership-summary",
    response_model=OwnershipOpsSummary,
)
async def ownership_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("ownership", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_ownership_summary(db, building_id)
