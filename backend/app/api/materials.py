from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building_element import BuildingElement
from app.models.material import Material
from app.models.user import User
from app.models.zone import Zone
from app.schemas.material import MaterialCreate, MaterialRead

router = APIRouter()


async def _verify_full_chain(db: AsyncSession, building_id: UUID, zone_id: UUID, element_id: UUID) -> BuildingElement:
    """Verify building -> zone -> element chain and return the element."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    result = await db.execute(select(Zone).where(Zone.id == zone_id, Zone.building_id == building_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

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


@router.get(
    "/buildings/{building_id}/zones/{zone_id}/elements/{element_id}/materials",
    response_model=list[MaterialRead],
)
async def list_materials_endpoint(
    building_id: UUID,
    zone_id: UUID,
    element_id: UUID,
    current_user: User = Depends(require_permission("materials", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all materials for a building element (not paginated)."""
    await _verify_full_chain(db, building_id, zone_id, element_id)

    result = await db.execute(select(Material).where(Material.element_id == element_id).order_by(Material.created_at))
    return result.scalars().all()


@router.post(
    "/buildings/{building_id}/zones/{zone_id}/elements/{element_id}/materials",
    response_model=MaterialRead,
    status_code=201,
)
async def create_material_endpoint(
    building_id: UUID,
    zone_id: UUID,
    element_id: UUID,
    data: MaterialCreate,
    current_user: User = Depends(require_permission("materials", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new material for a building element."""
    await _verify_full_chain(db, building_id, zone_id, element_id)

    material = Material(
        element_id=element_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


@router.delete(
    "/buildings/{building_id}/zones/{zone_id}/elements/{element_id}/materials/{material_id}",
    status_code=204,
)
async def delete_material_endpoint(
    building_id: UUID,
    zone_id: UUID,
    element_id: UUID,
    material_id: UUID,
    current_user: User = Depends(require_permission("materials", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a material. Verifies the full chain."""
    await _verify_full_chain(db, building_id, zone_id, element_id)

    result = await db.execute(
        select(Material).where(
            Material.id == material_id,
            Material.element_id == element_id,
        )
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    await db.delete(material)
    await db.commit()
