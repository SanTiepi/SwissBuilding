"""Tests for equipment lifecycle / replacement timeline service."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import patch

import pytest

from app.models.building import Building
from app.models.inventory_item import InventoryItem
from app.services.equipment_lifecycle_service import (
    DEFAULT_LIFESPAN,
    EQUIPMENT_LIFESPAN,
    _estimate_replacement_year,
    _is_critical,
    get_equipment_timeline,
)

# ── Helpers ────────────────────────────────────────────────────────

FIXED_TODAY = date(2026, 4, 1)


async def _create_building(db, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_item(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "item_type": "boiler",
        "name": "Boiler A",
    }
    defaults.update(kwargs)
    item = InventoryItem(**defaults)
    db.add(item)
    await db.flush()
    return item


# ── Unit: _estimate_replacement_year ──────────────────────────────


class TestEstimateReplacementYear:
    def test_warranty_takes_precedence(self):
        item = InventoryItem(
            item_type="boiler",
            name="B",
            installation_date=date(2010, 1, 1),
            warranty_end_date=date(2030, 6, 15),
        )
        assert _estimate_replacement_year(item) == 2030

    def test_installation_plus_lifespan(self):
        item = InventoryItem(
            item_type="elevator",
            name="E",
            installation_date=date(2000, 3, 1),
        )
        assert _estimate_replacement_year(item) == 2000 + EQUIPMENT_LIFESPAN["elevator"]

    def test_unknown_type_uses_default(self):
        item = InventoryItem(
            item_type="unknown_thing",
            name="U",
            installation_date=date(2015, 1, 1),
        )
        assert _estimate_replacement_year(item) == 2015 + DEFAULT_LIFESPAN

    def test_no_dates_returns_none(self):
        item = InventoryItem(item_type="boiler", name="B")
        assert _estimate_replacement_year(item) is None


# ── Unit: _is_critical ────────────────────────────────────────────


class TestIsCritical:
    def test_critical_condition(self):
        item = InventoryItem(item_type="boiler", name="B", condition="critical")
        assert _is_critical(item, 2035, FIXED_TODAY) is True

    def test_overdue_replacement(self):
        item = InventoryItem(item_type="boiler", name="B", condition="fair")
        assert _is_critical(item, 2025, FIXED_TODAY) is True

    def test_expired_warranty(self):
        item = InventoryItem(
            item_type="boiler",
            name="B",
            condition="fair",
            warranty_end_date=date(2025, 12, 31),
        )
        assert _is_critical(item, 2030, FIXED_TODAY) is True

    def test_good_item_not_critical(self):
        item = InventoryItem(
            item_type="boiler",
            name="B",
            condition="good",
            warranty_end_date=date(2030, 12, 31),
        )
        assert _is_critical(item, 2035, FIXED_TODAY) is False


# ── Integration: get_equipment_timeline ───────────────────────────


@pytest.mark.asyncio
async def test_empty_building(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    result = await get_equipment_timeline(db_session, building.id)
    assert result["item_count"] == 0
    assert result["total_forecast_cost_chf"] == 0.0
    assert result["critical_items_count"] == 0
    assert result["timeline"] == []


@pytest.mark.asyncio
@patch("app.services.equipment_lifecycle_service.date")
async def test_timeline_filters_by_window(mock_date, db_session, admin_user):
    mock_date.today.return_value = FIXED_TODAY

    building = await _create_building(db_session, admin_user)

    # Boiler: 2005+25=2030 → 4 years away → included in 10y window
    await _create_item(
        db_session,
        building.id,
        name="Old Boiler",
        item_type="boiler",
        installation_date=date(2005, 1, 1),
        replacement_cost_chf=25000.0,
        condition="poor",
    )
    # Heat pump: 2020+20=2040 → 14 years → excluded from 10y window
    await _create_item(
        db_session,
        building.id,
        name="New Heat Pump",
        item_type="heat_pump",
        installation_date=date(2020, 6, 1),
        replacement_cost_chf=35000.0,
        condition="good",
    )
    # Elevator: 2022+30=2052 → excluded
    await _create_item(
        db_session,
        building.id,
        name="Fresh Elevator",
        item_type="elevator",
        installation_date=date(2022, 1, 1),
        replacement_cost_chf=100000.0,
        condition="good",
    )

    result = await get_equipment_timeline(db_session, building.id, years=10)
    assert result["item_count"] == 1
    assert result["timeline"][0]["name"] == "Old Boiler"
    assert result["timeline"][0]["replacement_year"] == 2030
    assert result["total_forecast_cost_chf"] == 25000.0


@pytest.mark.asyncio
@patch("app.services.equipment_lifecycle_service.date")
async def test_critical_items_counted(mock_date, db_session, admin_user):
    mock_date.today.return_value = FIXED_TODAY

    building = await _create_building(db_session, admin_user)

    # HVAC: 2005+15=2020 → overdue → critical
    await _create_item(
        db_session,
        building.id,
        name="Broken HVAC",
        item_type="hvac",
        installation_date=date(2005, 1, 1),
        condition="critical",
        replacement_cost_chf=15000.0,
    )
    # Fire system: 2000+15=2015 → overdue → critical
    await _create_item(
        db_session,
        building.id,
        name="Overdue Fire System",
        item_type="fire_system",
        installation_date=date(2000, 1, 1),
        condition="poor",
        replacement_cost_chf=8000.0,
    )

    result = await get_equipment_timeline(db_session, building.id, years=10)
    assert result["critical_items_count"] == 2
    assert all(entry["critical"] for entry in result["timeline"])


@pytest.mark.asyncio
@patch("app.services.equipment_lifecycle_service.date")
async def test_sorted_by_replacement_year(mock_date, db_session, admin_user):
    mock_date.today.return_value = FIXED_TODAY

    building = await _create_building(db_session, admin_user)

    # Ventilation: 2015+20=2035
    await _create_item(
        db_session,
        building.id,
        name="Later",
        item_type="ventilation",
        installation_date=date(2015, 1, 1),
    )
    # Water heater: 2016+12=2028
    await _create_item(
        db_session,
        building.id,
        name="Sooner",
        item_type="water_heater",
        installation_date=date(2016, 1, 1),
    )

    result = await get_equipment_timeline(db_session, building.id, years=10)
    assert result["timeline"][0]["name"] == "Sooner"
    assert result["timeline"][1]["name"] == "Later"


@pytest.mark.asyncio
async def test_items_without_dates_skipped(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_item(db_session, building.id, name="Mystery Box")
    result = await get_equipment_timeline(db_session, building.id)
    assert result["item_count"] == 0


@pytest.mark.asyncio
@patch("app.services.equipment_lifecycle_service.date")
async def test_overdue_items_included(mock_date, db_session, admin_user):
    """Overdue items (negative years_until) should still appear in the timeline."""
    mock_date.today.return_value = FIXED_TODAY

    building = await _create_building(db_session, admin_user)
    # Appliance: 2005+10=2015 → 11 years overdue
    await _create_item(
        db_session,
        building.id,
        name="Ancient Appliance",
        item_type="appliance",
        installation_date=date(2005, 1, 1),
        replacement_cost_chf=2000.0,
    )

    result = await get_equipment_timeline(db_session, building.id, years=10)
    assert result["item_count"] == 1
    assert result["timeline"][0]["years_until_replacement"] < 0
    assert result["timeline"][0]["critical"] is True


@pytest.mark.asyncio
@patch("app.services.equipment_lifecycle_service.date")
async def test_all_lifespan_types_within_window(mock_date, db_session, admin_user):
    """All equipment types with old enough installation date appear in a 50y window."""
    mock_date.today.return_value = FIXED_TODAY

    building = await _create_building(db_session, admin_user)
    for item_type in EQUIPMENT_LIFESPAN:
        await _create_item(
            db_session,
            building.id,
            item_type=item_type,
            name=f"Test {item_type}",
            installation_date=date(2000, 1, 1),
        )

    result = await get_equipment_timeline(db_session, building.id, years=50)
    types_in_result = {e["type"] for e in result["timeline"]}
    assert types_in_result == set(EQUIPMENT_LIFESPAN.keys())
