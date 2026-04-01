import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.activity import ActivityItemRead
from app.schemas.building import BuildingCreate, BuildingListRead, BuildingRead, BuildingUpdate
from app.schemas.common import PaginatedResponse
from app.services.audit_service import log_action
from app.services.building_service import (
    create_building,
    delete_building,
    get_building,
    list_buildings,
    update_building,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=PaginatedResponse[BuildingListRead])
async def list_buildings_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    canton: str | None = None,
    city: str | None = None,
    postal_code: str | None = None,
    building_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    search: str | None = None,
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List buildings with filtering and pagination."""
    buildings_list, total = await list_buildings(
        db, page, size, canton, city, postal_code, building_type, year_from, year_to, search
    )
    pages = (total + size - 1) // size
    return {
        "items": buildings_list,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post("", response_model=BuildingRead, status_code=201)
async def create_building_endpoint(
    data: BuildingCreate,
    current_user: User = Depends(require_permission("buildings", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new building."""
    building = await create_building(
        db,
        data,
        current_user.id,
        organization_id=current_user.organization_id,
    )
    await log_action(db, current_user.id, "create", "building", building.id)
    try:
        from app.services.search_service import index_building

        index_building(building)
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)
    return building


@router.get("/{building_id}", response_model=BuildingRead)
async def get_building_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single building by ID."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.put("/{building_id}", response_model=BuildingRead)
async def update_building_endpoint(
    building_id: UUID,
    data: BuildingUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing building."""
    building = await update_building(db, building_id, data)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    await log_action(db, current_user.id, "update", "building", building_id)
    try:
        from app.services.search_service import index_building

        index_building(building)
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)
    return building


@router.delete("/{building_id}", status_code=204)
async def delete_building_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a building."""
    success = await delete_building(db, building_id)
    if not success:
        raise HTTPException(status_code=404, detail="Building not found")
    await log_action(db, current_user.id, "delete", "building", building_id)
    try:
        from app.services.search_service import delete_building as search_delete_building

        search_delete_building(str(building_id))
    except Exception:
        logger.warning("Search index operation failed", exc_info=True)


@router.get("/{building_id}/activity", response_model=list[ActivityItemRead])
async def get_building_activity_endpoint(
    building_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated activity timeline for a building."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from app.services.activity_service import get_building_activity

    return await get_building_activity(db, building_id, limit=limit, offset=offset)
