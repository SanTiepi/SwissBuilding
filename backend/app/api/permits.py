"""Permit workflow API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.permit import PermitAlert, PermitCreate, PermitRead, PermitUpdate
from app.services.permit_service import (
    create_permit,
    delete_permit,
    get_building_permits,
    get_permit,
    get_permit_alerts,
    update_permit,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_permit_or_404(db: AsyncSession, permit_id: UUID):
    permit = await get_permit(db, permit_id)
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")
    return permit


# ---------------------------------------------------------------------------
# Permit CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/permits",
    response_model=PermitRead,
    status_code=201,
    tags=["Permits"],
)
async def create_permit_endpoint(
    building_id: UUID,
    payload: PermitCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new permit for a building."""
    await _get_building_or_404(db, building_id)

    permit = await create_permit(
        db,
        building_id,
        permit_type=payload.permit_type,
        issued_date=payload.issued_date,
        expiry_date=payload.expiry_date,
        subsidy_amount=payload.subsidy_amount,
        notes=payload.notes,
    )
    await db.commit()
    return permit


@router.get(
    "/buildings/{building_id}/permits",
    response_model=list[PermitRead],
    tags=["Permits"],
)
async def list_permits_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all permits for a building."""
    await _get_building_or_404(db, building_id)
    permits = await get_building_permits(db, building_id)
    return permits


@router.get(
    "/buildings/{building_id}/permits/{permit_id}",
    response_model=PermitRead,
    tags=["Permits"],
)
async def get_permit_endpoint(
    building_id: UUID,
    permit_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single permit."""
    await _get_building_or_404(db, building_id)
    permit = await _get_permit_or_404(db, permit_id)

    if permit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Permit not found")

    return permit


@router.patch(
    "/buildings/{building_id}/permits/{permit_id}",
    response_model=PermitRead,
    tags=["Permits"],
)
async def update_permit_endpoint(
    building_id: UUID,
    permit_id: UUID,
    payload: PermitUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update permit status or dates."""
    await _get_building_or_404(db, building_id)
    permit = await _get_permit_or_404(db, permit_id)

    if permit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Permit not found")

    updates = payload.model_dump(exclude_unset=True)
    updated_permit = await update_permit(db, permit_id, **updates)
    await db.commit()
    return updated_permit


@router.delete(
    "/buildings/{building_id}/permits/{permit_id}",
    status_code=204,
    tags=["Permits"],
)
async def delete_permit_endpoint(
    building_id: UUID,
    permit_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a permit."""
    await _get_building_or_404(db, building_id)
    permit = await _get_permit_or_404(db, permit_id)

    if permit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Permit not found")

    await delete_permit(db, permit_id)
    await db.commit()


# ---------------------------------------------------------------------------
# Deadline Tracking
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/permits/alerts",
    response_model=list[PermitAlert],
    tags=["Permits"],
)
async def get_permit_alerts_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get deadline alerts for expiring permits."""
    await _get_building_or_404(db, building_id)
    alerts = await get_permit_alerts(db, building_id)
    return alerts
