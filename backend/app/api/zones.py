from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building_element import BuildingElement
from app.models.user import User
from app.models.zone import Zone
from app.schemas.common import PaginatedResponse
from app.schemas.zone import ZoneCreate, ZoneRead, ZoneUpdate

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_zone_or_404(db: AsyncSession, building_id: UUID, zone_id: UUID) -> Zone:
    result = await db.execute(select(Zone).where(Zone.id == zone_id, Zone.building_id == building_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


async def _enrich_zone(db: AsyncSession, zone: Zone) -> dict:
    """Return zone data with computed children_count and elements_count."""
    children_result = await db.execute(select(func.count()).select_from(Zone).where(Zone.parent_zone_id == zone.id))
    children_count = children_result.scalar() or 0

    elements_result = await db.execute(
        select(func.count()).select_from(BuildingElement).where(BuildingElement.zone_id == zone.id)
    )
    elements_count = elements_result.scalar() or 0

    zone_dict = {c.key: getattr(zone, c.key) for c in zone.__table__.columns}
    zone_dict["children_count"] = children_count
    zone_dict["elements_count"] = elements_count
    return zone_dict


@router.get("/buildings/{building_id}/zones", response_model=PaginatedResponse[ZoneRead])
async def list_zones_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    zone_type: str | None = None,
    parent_zone_id: str | None = None,
    current_user: User = Depends(require_permission("zones", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List zones for a building with optional filters and pagination."""
    await _get_building_or_404(db, building_id)

    query = select(Zone).where(Zone.building_id == building_id)
    count_query = select(func.count()).select_from(Zone).where(Zone.building_id == building_id)

    if zone_type is not None:
        query = query.where(Zone.zone_type == zone_type)
        count_query = count_query.where(Zone.zone_type == zone_type)

    if parent_zone_id is not None:
        pid = UUID(parent_zone_id)
        query = query.where(Zone.parent_zone_id == pid)
        count_query = count_query.where(Zone.parent_zone_id == pid)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    pages = (total + size - 1) // size if total > 0 else 0

    query = query.order_by(Zone.created_at).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    zones = result.scalars().all()

    items = [await _enrich_zone(db, z) for z in zones]
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.post("/buildings/{building_id}/zones", response_model=ZoneRead, status_code=201)
async def create_zone_endpoint(
    building_id: UUID,
    data: ZoneCreate,
    current_user: User = Depends(require_permission("zones", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new zone for a building."""
    await _get_building_or_404(db, building_id)

    zone = Zone(
        building_id=building_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return await _enrich_zone(db, zone)


@router.get(
    "/buildings/{building_id}/zones/{zone_id}",
    response_model=ZoneRead,
)
async def get_zone_endpoint(
    building_id: UUID,
    zone_id: UUID,
    current_user: User = Depends(require_permission("zones", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single zone with children_count and elements_count."""
    await _get_building_or_404(db, building_id)
    zone = await _get_zone_or_404(db, building_id, zone_id)
    return await _enrich_zone(db, zone)


@router.put(
    "/buildings/{building_id}/zones/{zone_id}",
    response_model=ZoneRead,
)
async def update_zone_endpoint(
    building_id: UUID,
    zone_id: UUID,
    data: ZoneUpdate,
    current_user: User = Depends(require_permission("zones", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing zone."""
    await _get_building_or_404(db, building_id)
    zone = await _get_zone_or_404(db, building_id, zone_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    await db.commit()
    await db.refresh(zone)
    return await _enrich_zone(db, zone)


@router.delete("/buildings/{building_id}/zones/{zone_id}", status_code=204)
async def delete_zone_endpoint(
    building_id: UUID,
    zone_id: UUID,
    current_user: User = Depends(require_permission("zones", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a zone. Refuses if zone has children zones or elements."""
    await _get_building_or_404(db, building_id)
    zone = await _get_zone_or_404(db, building_id, zone_id)

    # Check for children zones
    children_result = await db.execute(select(func.count()).select_from(Zone).where(Zone.parent_zone_id == zone.id))
    if (children_result.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete zone with child zones. Remove children first.",
        )

    # Check for elements
    elements_result = await db.execute(
        select(func.count()).select_from(BuildingElement).where(BuildingElement.zone_id == zone.id)
    )
    if (elements_result.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete zone with elements. Remove elements first.",
        )

    await db.delete(zone)
    await db.commit()
