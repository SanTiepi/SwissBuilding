from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building_element import BuildingElement
from app.models.material import Material
from app.models.user import User
from app.models.zone import Zone
from app.schemas.building_element import (
    BuildingElementCreate,
    BuildingElementRead,
    BuildingElementUpdate,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


async def _get_zone_in_building(db: AsyncSession, building_id: UUID, zone_id: UUID) -> Zone:
    """Verify zone exists and belongs to the building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    result = await db.execute(select(Zone).where(Zone.id == zone_id, Zone.building_id == building_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


async def _get_element_or_404(db: AsyncSession, building_id: UUID, zone_id: UUID, element_id: UUID) -> BuildingElement:
    """Verify the full chain: building -> zone -> element."""
    await _get_zone_in_building(db, building_id, zone_id)

    result = await db.execute(
        select(BuildingElement).where(
            BuildingElement.id == element_id,
            BuildingElement.zone_id == zone_id,
        )
    )
    element = result.scalar_one_or_none()
    if not element:
        raise HTTPException(status_code=404, detail="Element not found")
    return element


async def _enrich_element(db: AsyncSession, element: BuildingElement) -> dict:
    """Return element data with computed materials_count."""
    materials_result = await db.execute(
        select(func.count()).select_from(Material).where(Material.element_id == element.id)
    )
    materials_count = materials_result.scalar() or 0

    element_dict = {c.key: getattr(element, c.key) for c in element.__table__.columns}
    element_dict["materials_count"] = materials_count
    return element_dict


@router.get(
    "/buildings/{building_id}/zones/{zone_id}/elements",
    response_model=PaginatedResponse[BuildingElementRead],
)
async def list_elements_endpoint(
    building_id: UUID,
    zone_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    element_type: str | None = None,
    current_user: User = Depends(require_permission("elements", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List building elements for a zone with optional filters and pagination."""
    await _get_zone_in_building(db, building_id, zone_id)

    query = select(BuildingElement).where(BuildingElement.zone_id == zone_id)
    count_query = select(func.count()).select_from(BuildingElement).where(BuildingElement.zone_id == zone_id)

    if element_type is not None:
        query = query.where(BuildingElement.element_type == element_type)
        count_query = count_query.where(BuildingElement.element_type == element_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    pages = (total + size - 1) // size if total > 0 else 0

    query = query.order_by(BuildingElement.created_at).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    elements = result.scalars().all()

    items = [await _enrich_element(db, e) for e in elements]
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.post(
    "/buildings/{building_id}/zones/{zone_id}/elements",
    response_model=BuildingElementRead,
    status_code=201,
)
async def create_element_endpoint(
    building_id: UUID,
    zone_id: UUID,
    data: BuildingElementCreate,
    current_user: User = Depends(require_permission("elements", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new building element in a zone."""
    await _get_zone_in_building(db, building_id, zone_id)

    element = BuildingElement(
        zone_id=zone_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(element)
    await db.commit()
    await db.refresh(element)
    return await _enrich_element(db, element)


@router.get(
    "/buildings/{building_id}/zones/{zone_id}/elements/{element_id}",
    response_model=BuildingElementRead,
)
async def get_element_endpoint(
    building_id: UUID,
    zone_id: UUID,
    element_id: UUID,
    current_user: User = Depends(require_permission("elements", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single building element with materials_count."""
    element = await _get_element_or_404(db, building_id, zone_id, element_id)
    return await _enrich_element(db, element)


@router.put(
    "/buildings/{building_id}/zones/{zone_id}/elements/{element_id}",
    response_model=BuildingElementRead,
)
async def update_element_endpoint(
    building_id: UUID,
    zone_id: UUID,
    element_id: UUID,
    data: BuildingElementUpdate,
    current_user: User = Depends(require_permission("elements", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing building element."""
    element = await _get_element_or_404(db, building_id, zone_id, element_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(element, field, value)

    await db.commit()
    await db.refresh(element)
    return await _enrich_element(db, element)


@router.delete(
    "/buildings/{building_id}/zones/{zone_id}/elements/{element_id}",
    status_code=204,
)
async def delete_element_endpoint(
    building_id: UUID,
    zone_id: UUID,
    element_id: UUID,
    current_user: User = Depends(require_permission("elements", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a building element. Refuses if element has materials."""
    element = await _get_element_or_404(db, building_id, zone_id, element_id)

    materials_result = await db.execute(
        select(func.count()).select_from(Material).where(Material.element_id == element.id)
    )
    if (materials_result.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete element with materials. Remove materials first.",
        )

    await db.delete(element)
    await db.commit()
