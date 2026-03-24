"""BatiConnect — Lease Ops API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.lease import Lease
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.lease import LeaseCreate, LeaseListRead, LeaseRead, LeaseUpdate
from app.schemas.lease_summary import LeaseOpsSummary
from app.services.lease_service import (
    create_lease,
    enrich_lease,
    enrich_leases,
    get_lease,
    get_lease_summary,
    list_leases,
    update_lease,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_lease_or_404(db: AsyncSession, lease_id: UUID) -> Lease:
    lease = await get_lease(db, lease_id)
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")
    return lease


@router.get(
    "/buildings/{building_id}/leases",
    response_model=PaginatedResponse[LeaseListRead],
)
async def list_leases_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    lease_type: str | None = None,
    current_user: User = Depends(require_permission("leases", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    items, total = await list_leases(db, building_id, page=page, size=size, status=status, lease_type=lease_type)
    pages = (total + size - 1) // size if total > 0 else 0
    enriched = await enrich_leases(db, items)
    return {"items": enriched, "total": total, "page": page, "size": size, "pages": pages}


@router.post(
    "/buildings/{building_id}/leases",
    response_model=LeaseRead,
    status_code=201,
)
async def create_lease_endpoint(
    building_id: UUID,
    payload: LeaseCreate,
    current_user: User = Depends(require_permission("leases", "create")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    data.pop("building_id", None)  # use path param
    lease = await create_lease(db, building_id, data, created_by=current_user.id)
    await db.commit()
    return await enrich_lease(db, lease)


@router.get(
    "/leases/{lease_id}",
    response_model=LeaseRead,
)
async def get_lease_endpoint(
    lease_id: UUID,
    current_user: User = Depends(require_permission("leases", "read")),
    db: AsyncSession = Depends(get_db),
):
    lease = await _get_lease_or_404(db, lease_id)
    return await enrich_lease(db, lease)


@router.put(
    "/leases/{lease_id}",
    response_model=LeaseRead,
)
async def update_lease_endpoint(
    lease_id: UUID,
    payload: LeaseUpdate,
    current_user: User = Depends(require_permission("leases", "update")),
    db: AsyncSession = Depends(get_db),
):
    lease = await _get_lease_or_404(db, lease_id)
    data = payload.model_dump(exclude_unset=True)
    updated = await update_lease(db, lease, data)
    await db.commit()
    return await enrich_lease(db, updated)


@router.get(
    "/buildings/{building_id}/lease-summary",
    response_model=LeaseOpsSummary,
)
async def lease_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("leases", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_lease_summary(db, building_id)
