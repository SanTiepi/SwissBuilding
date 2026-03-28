"""API routes for building life calendar."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.building_life_service import get_annual_review, get_building_calendar

router = APIRouter()


@router.get("/buildings/{building_id}/calendar")
async def building_calendar(
    building_id: uuid.UUID,
    horizon: int = Query(default=365, ge=30, le=1095),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get building life calendar with all upcoming events."""
    result = await get_building_calendar(db, building_id, horizon)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/buildings/{building_id}/annual-review")
async def building_annual_review(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get annual review summary for a building."""
    result = await get_annual_review(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
