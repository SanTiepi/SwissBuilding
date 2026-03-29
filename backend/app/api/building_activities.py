"""Building Activity Ledger API — opposable multi-actor audit trail."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_activity import (
    BuildingActivityListRead,
    ChainIntegrityRead,
)
from app.services import activity_ledger_service as svc

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/activities",
    response_model=BuildingActivityListRead,
)
async def list_building_activities(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    actor_id: UUID | None = None,
    activity_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable activity ledger for a building."""
    await _get_building_or_404(db, building_id)
    items, total = await svc.get_building_ledger(
        db,
        building_id,
        page=page,
        size=size,
        actor_id=actor_id,
        activity_type=activity_type,
        date_from=date_from,
        date_to=date_to,
    )
    return {"items": items, "total": total, "page": page, "size": size}


@router.get(
    "/buildings/{building_id}/activities/verify-chain",
    response_model=ChainIntegrityRead,
)
async def verify_chain(
    building_id: UUID,
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Verify the hash chain integrity for a building's activity ledger."""
    await _get_building_or_404(db, building_id)
    return await svc.verify_chain_integrity(db, building_id)
