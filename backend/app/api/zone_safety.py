"""Zone-level safety status and occupant notices API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.zone_safety import (
    OccupantNoticeCreate,
    OccupantNoticeRead,
    ZoneSafetyStatusCreate,
    ZoneSafetyStatusRead,
)
from app.services.zone_safety_service import (
    assess_zone_safety,
    create_notice,
    get_active_notices,
    get_building_safety_summary,
    get_zone_safety,
    list_notices,
    publish_notice,
)

router = APIRouter()


@router.post("/zones/{zone_id}/safety", response_model=ZoneSafetyStatusRead, status_code=201)
async def assess_zone_safety_endpoint(
    zone_id: UUID,
    data: ZoneSafetyStatusCreate,
    building_id: UUID = Query(..., description="Building the zone belongs to"),
    current_user: User = Depends(require_permission("zones", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Assess or update zone safety status."""
    try:
        status = await assess_zone_safety(db, zone_id, building_id, data, assessed_by=current_user.id)
        await db.commit()
        await db.refresh(status)
        return status
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/zones/{zone_id}/safety", response_model=ZoneSafetyStatusRead | None)
async def get_zone_safety_endpoint(
    zone_id: UUID,
    current_user: User = Depends(require_permission("zones", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get current safety status for a zone."""
    return await get_zone_safety(db, zone_id)


@router.get("/buildings/{building_id}/safety-summary")
async def get_building_safety_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get building-wide zone safety summary."""
    return await get_building_safety_summary(db, building_id)


@router.post("/buildings/{building_id}/notices", response_model=OccupantNoticeRead, status_code=201)
async def create_notice_endpoint(
    building_id: UUID,
    data: OccupantNoticeCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a draft occupant notice."""
    try:
        notice = await create_notice(db, building_id, data, created_by=current_user.id)
        await db.commit()
        await db.refresh(notice)
        return notice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/notices/{notice_id}/publish", response_model=OccupantNoticeRead)
async def publish_notice_endpoint(
    notice_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Publish a draft notice."""
    try:
        notice = await publish_notice(db, notice_id)
        await db.commit()
        await db.refresh(notice)
        return notice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/buildings/{building_id}/notices", response_model=list[OccupantNoticeRead])
async def list_notices_endpoint(
    building_id: UUID,
    status: str | None = None,
    active_only: bool = False,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List notices for a building. Use active_only=true for published + not expired."""
    if active_only:
        return await get_active_notices(db, building_id)
    return await list_notices(db, building_id, status=status)
