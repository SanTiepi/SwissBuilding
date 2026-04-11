"""Tests for inventory item CRUD + warranty alerts + replacement cost timeline."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.inventory_item import InventoryItem
from app.services.inventory_management_service import (
    check_warranty_expiry,
    get_replacement_cost_timeline,
)


@pytest.fixture
async def building(db: AsyncSession):
    b = Building(
        id=uuid.uuid4(),
        egrid="CH999000000001",
        egid=99901,
        address="1 Rue Inventaire, Lausanne",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="apartment",
        construction_year=1985,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(b)
    await db.flush()
    return b


@pytest.fixture
async def inventory_item(db: AsyncSession, building: Building):
    item = InventoryItem(
        id=uuid.uuid4(),
        building_id=building.id,
        item_type="boiler",
        name="Viessmann Vitodens 200-W",
        manufacturer="Viessmann",
        model="Vitodens 200-W",
        serial_number="VS-2024-001",
        installation_date=date(2020, 3, 15),
        warranty_end_date=date.today() + timedelta(days=30),
        condition="good",
        purchase_cost_chf=12000.0,
        replacement_cost_chf=15000.0,
        notes="Installed during renovation",
    )
    db.add(item)
    await db.flush()
    return item


class TestInventoryItemCRUD:
    """Test basic CRUD operations on InventoryItem model."""

    async def test_create_inventory_item(self, db: AsyncSession, building: Building):
        item = InventoryItem(
            id=uuid.uuid4(),
            building_id=building.id,
            item_type="elevator",
            name="Schindler 3300",
            manufacturer="Schindler",
            condition="fair",
            replacement_cost_chf=80000.0,
        )
        db.add(item)
        await db.flush()

        assert item.id is not None
        assert item.item_type == "elevator"
        assert item.building_id == building.id

    async def test_read_inventory_item(self, db: AsyncSession, inventory_item: InventoryItem):
        from sqlalchemy import select

        result = await db.execute(
            select(InventoryItem).where(InventoryItem.id == inventory_item.id)
        )
        item = result.scalar_one_or_none()
        assert item is not None
        assert item.name == "Viessmann Vitodens 200-W"
        assert item.item_type == "boiler"
        assert item.manufacturer == "Viessmann"

    async def test_update_inventory_item(self, db: AsyncSession, inventory_item: InventoryItem):
        inventory_item.condition = "fair"
        inventory_item.notes = "Annual service completed"
        await db.flush()

        from sqlalchemy import select

        result = await db.execute(
            select(InventoryItem).where(InventoryItem.id == inventory_item.id)
        )
        updated = result.scalar_one()
        assert updated.condition == "fair"
        assert updated.notes == "Annual service completed"

    async def test_delete_inventory_item(self, db: AsyncSession, inventory_item: InventoryItem):
        item_id = inventory_item.id
        await db.delete(inventory_item)
        await db.flush()

        from sqlalchemy import select

        result = await db.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_list_items_by_building(self, db: AsyncSession, building: Building):
        for i, itype in enumerate(["hvac", "boiler", "elevator"]):
            db.add(InventoryItem(
                id=uuid.uuid4(),
                building_id=building.id,
                item_type=itype,
                name=f"Equipment {i}",
                condition="good",
            ))
        await db.flush()

        from sqlalchemy import select

        result = await db.execute(
            select(InventoryItem).where(InventoryItem.building_id == building.id)
        )
        items = result.scalars().all()
        assert len(items) == 3
        types = {i.item_type for i in items}
        assert types == {"hvac", "boiler", "elevator"}


class TestWarrantyAlert:
    """Test warranty expiry notification logic."""

    async def test_warranty_expiring_soon_creates_notification(
        self, db: AsyncSession, inventory_item: InventoryItem
    ):
        user_id = uuid.uuid4()
        alert = await check_warranty_expiry(db, inventory_item, user_id)
        assert alert is not None
        assert alert["severity"] == "high"
        assert alert["days_until_expiry"] <= 30
        assert "notification_id" in alert

    async def test_no_alert_if_warranty_far(self, db: AsyncSession, building: Building):
        item = InventoryItem(
            id=uuid.uuid4(),
            building_id=building.id,
            item_type="solar_panel",
            name="SunPower SPR-X22",
            warranty_end_date=date.today() + timedelta(days=365),
            condition="good",
        )
        db.add(item)
        await db.flush()

        alert = await check_warranty_expiry(db, item, uuid.uuid4())
        assert alert is None

    async def test_no_alert_if_no_warranty(self, db: AsyncSession, building: Building):
        item = InventoryItem(
            id=uuid.uuid4(),
            building_id=building.id,
            item_type="furniture",
            name="Office desk",
            condition="good",
        )
        db.add(item)
        await db.flush()

        alert = await check_warranty_expiry(db, item, uuid.uuid4())
        assert alert is None


class TestReplacementCostTimeline:
    """Test replacement cost forecasting."""

    async def test_replacement_cost_aggregation(self, db: AsyncSession, building: Building):
        # Old boiler → needs replacement within 5y
        db.add(InventoryItem(
            id=uuid.uuid4(),
            building_id=building.id,
            item_type="boiler",
            name="Old Boiler",
            installation_date=date(2005, 1, 1),
            replacement_cost_chf=15000.0,
            condition="poor",
        ))
        # Recent solar panel → no replacement needed soon
        db.add(InventoryItem(
            id=uuid.uuid4(),
            building_id=building.id,
            item_type="solar_panel",
            name="New Solar Panel",
            installation_date=date(2024, 6, 1),
            replacement_cost_chf=25000.0,
            condition="good",
        ))
        await db.flush()

        timeline = await get_replacement_cost_timeline(db, building.id)

        assert timeline["building_id"] == str(building.id)
        assert timeline["total_5y_chf"] >= 15000.0  # at least the old boiler
        assert len(timeline["by_type"]) == 2
        assert any(t["item_type"] == "boiler" for t in timeline["by_type"])
