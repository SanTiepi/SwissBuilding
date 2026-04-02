# Task C.1 — Inventaire Equipements CRUD Complet

## What to do
Complete the CRUD endpoints for InventoryItem (14 types: hvac, boiler, elevator, fire_system, electrical_panel, solar_panel, heat_pump, ventilation, water_heater, garage_door, intercom, appliance, furniture, other).

Create/enhance:
- POST /buildings/{building_id}/inventory — create item
- GET /buildings/{building_id}/inventory — list all items
- GET /buildings/{building_id}/inventory/{item_id} — read one
- PATCH /buildings/{building_id}/inventory/{item_id} — update
- DELETE /buildings/{building_id}/inventory/{item_id} — delete
- POST /buildings/{building_id}/inventory/{item_id}/warranty-alert — trigger warranty expiry notification

Add optional aggregation endpoint:
- GET /buildings/{building_id}/inventory/timeline/replacement-costs — forecast 5/10 year replacement costs

## Files to create/modify
- **Modify:** `backend/app/api/material_inventory.py` - add/complete CRUD routes (~80 lines)
- **Create/Enhance:** `backend/app/services/inventory_management_service.py` (~120 lines) if not exists
- **Modify:** `backend/app/schemas/inventory_item.py` - ensure complete schema (~50 lines)
- **Create:** `backend/tests/test_inventory_crud.py` (~120 lines, 8 tests)

## Existing patterns to copy

From `backend/app/models/inventory_item.py` (already read):
```python
class InventoryItem(ProvenanceMixin, Base):
    __tablename__ = "inventory_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    item_type = Column(String(50))  # 14 types
    name = Column(String(255))
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    installation_date = Column(Date, nullable=True)
    warranty_end_date = Column(Date, nullable=True)
    condition = Column(String(20))  # good | fair | poor | critical | unknown
    purchase_cost_chf = Column(Float, nullable=True)
    replacement_cost_chf = Column(Float, nullable=True)
    # ... more fields
```

From `backend/app/api/action_items.py` (CRUD pattern):
```python
@router.post("/buildings/{building_id}/inventory")
async def create_inventory_item(
    building_id: UUID,
    payload: InventoryItemCreateSchema,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new inventory item."""
    building = await db.execute(select(Building).where(Building.id == building_id))
    if not building.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Building not found")
    
    item = InventoryItem(
        building_id=building_id,
        item_type=payload.item_type,
        name=payload.name,
        installation_date=payload.installation_date,
        warranty_end_date=payload.warranty_end_date,
        condition=payload.condition,
        replacement_cost_chf=payload.replacement_cost_chf,
    )
    db.add(item)
    await db.commit()
    return item

@router.get("/buildings/{building_id}/inventory")
async def list_inventory_items(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all inventory items for building."""
    items = await db.execute(
        select(InventoryItem).where(InventoryItem.building_id == building_id).order_by(InventoryItem.item_type)
    )
    return items.scalars().all()

@router.get("/buildings/{building_id}/inventory/{item_id}")
async def get_inventory_item(
    building_id: UUID,
    item_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id, InventoryItem.building_id == building_id)
    )
    if not item.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/buildings/{building_id}/inventory/{item_id}")
async def update_inventory_item(
    building_id: UUID,
    item_id: UUID,
    payload: InventoryItemUpdateSchema,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id, InventoryItem.building_id == building_id)
    )
    item = item.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    return item

@router.delete("/buildings/{building_id}/inventory/{item_id}")
async def delete_inventory_item(
    building_id: UUID,
    item_id: UUID,
    current_user: User = Depends(require_permission("buildings", "delete")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id, InventoryItem.building_id == building_id)
    )
    item = item.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(item)
    await db.commit()
    return {"deleted": True}
```

## Commit message
```
feat(programme-c): inventory management CRUD complete (14 item types + warranty alerts + replacement cost timeline)
```

## Test command
```bash
cd backend && python -m pytest tests/test_inventory_crud.py -v
```

## Notes
- Item types: hvac, boiler, elevator, fire_system, electrical_panel, solar_panel, heat_pump, ventilation, water_heater, garage_door, intercom, appliance, furniture, other
- Condition: good, fair, poor, critical, unknown (enum or string)
- Warranty expiry automatic trigger → notification service
- Replacement cost timeline: aggregate by type, sum, project 5/10y forecast
- No external calls, all data local
