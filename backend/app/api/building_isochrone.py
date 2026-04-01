"""Building isochrone API -- Mapbox isochrone contours for mobility analysis."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.isochrone import IsochroneResponse
from app.services.isochrone_service import get_building_isochrone

router = APIRouter()


@router.get("/buildings/{building_id}/isochrone", response_model=IsochroneResponse)
async def get_isochrone(
    building_id: uuid.UUID,
    profile: str = "walking",
    range_list: str = "5,10,15",
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get isochrone contours (5/10/15 min) for a building."""
    try:
        ranges = [int(r.strip()) for r in range_list.split(",") if r.strip()]
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail="Invalid range_list format. Expected comma-separated integers."
        ) from e

    try:
        result = await get_building_isochrone(db, building_id, profile, minutes_list=ranges)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return result
