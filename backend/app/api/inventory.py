"""Inventory item CRUD endpoints (14 equipment types)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.inventory_item import InventoryItem
from app.models.user import User
from app.schemas.inventory_item import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
)
from app.services.inventory_management_service import (
    check_warranty_expiry,
    get_replacement_cost_timeline,
)

router = APIRouter()


@router.post("/buildings/{building_id}/inventory", response_model=InventoryItemRead)
async def create_inventory_item(
    building_id: uuid.UUID,
    payload: InventoryItemCreate,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new inventory item for a building."""
    building = await db.execute(select(Building).where(Building.id == building_id))
    if not building.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Building not found")

    item = InventoryItem(
        building_id=building_id,
        zone_id=payload.zone_id,
        item_type=payload.item_type,
        name=payload.name,
        manufacturer=payload.manufacturer,
        model=payload.model,
        serial_number=payload.serial_number,
        installation_date=payload.installation_date,
        warranty_end_date=payload.warranty_end_date,
        condition=payload.condition,
        purchase_cost_chf=payload.purchase_cost_chf,
        replacement_cost_chf=payload.replacement_cost_chf,
        maintenance_contract_id=payload.maintenance_contract_id,
        notes=payload.notes,
        created_by=current_user.id,
        source_type=payload.source_type,
        confidence=payload.confidence,
        source_ref=payload.source_ref,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/buildings/{building_id}/inventory", response_model=list[InventoryItemRead])
async def list_inventory_items(
    building_id: uuid.UUID,
    item_type: str | None = None,
    condition: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all inventory items for a building, with optional type/condition filters."""
    query = select(InventoryItem).where(InventoryItem.building_id == building_id)
    if item_type:
        query = query.where(InventoryItem.item_type == item_type)
    if condition:
        query = query.where(InventoryItem.condition == condition)
    query = query.order_by(InventoryItem.item_type, InventoryItem.name)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/buildings/{building_id}/inventory/{item_id}", response_model=InventoryItemRead)
async def get_inventory_item(
    building_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single inventory item."""
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id,
            InventoryItem.building_id == building_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/buildings/{building_id}/inventory/{item_id}", response_model=InventoryItemRead)
async def update_inventory_item(
    building_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: InventoryItemUpdate,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Update an inventory item."""
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id,
            InventoryItem.building_id == building_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/buildings/{building_id}/inventory/{item_id}")
async def delete_inventory_item(
    building_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete an inventory item."""
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id,
            InventoryItem.building_id == building_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await db.commit()
    return {"deleted": True}


@router.post("/buildings/{building_id}/inventory/{item_id}/warranty-alert")
async def trigger_warranty_alert(
    building_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a warranty expiry notification for an inventory item."""
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id,
            InventoryItem.building_id == building_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    alert = await check_warranty_expiry(db, item, current_user.id)
    await db.commit()

    if alert is None:
        return {"triggered": False, "reason": "No warranty alert applicable (no warranty, >90 days, or already notified)"}
    return {"triggered": True, "alert": alert}


@router.get("/buildings/{building_id}/inventory/timeline/replacement-costs")
async def replacement_cost_timeline(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Forecast 5/10-year replacement costs for all inventory items."""
    building = await db.execute(select(Building).where(Building.id == building_id))
    if not building.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_replacement_cost_timeline(db, building_id)
