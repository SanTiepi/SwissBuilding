"""Building Dashboard aggregate API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_dashboard import BuildingDashboard
from app.services.building_dashboard_service import (
    get_building_dashboard,
    get_buildings_dashboard_list,
    get_dashboard_quick,
)

router = APIRouter()


@router.get("/buildings/{building_id}/dashboard", response_model=BuildingDashboard)
async def building_dashboard(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return a complete dashboard aggregate for a single building."""
    result = await get_building_dashboard(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.post("/buildings/dashboards", response_model=list[BuildingDashboard])
async def batch_building_dashboards(
    body: Annotated[dict, Body()],
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return dashboards for multiple buildings (max 20)."""
    building_ids_raw = body.get("building_ids", [])
    if not building_ids_raw:
        return []

    # Parse and limit
    try:
        building_ids = [uuid.UUID(str(bid)) for bid in building_ids_raw]
    except (ValueError, AttributeError) as e:
        raise HTTPException(status_code=422, detail="Invalid building_id format") from e

    max_limit = body.get("max", 20)
    if not isinstance(max_limit, int) or max_limit < 1:
        max_limit = 20
    building_ids = building_ids[:max_limit]

    return await get_buildings_dashboard_list(db, building_ids)


@router.get("/buildings/{building_id}/dashboard/quick")
async def building_dashboard_quick(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return a lightweight dashboard with only counts and grade/risk."""
    result = await get_dashboard_quick(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
