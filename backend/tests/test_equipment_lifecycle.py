"""Tests for equipment_lifecycle_service — replacement timeline and CAPEX forecast."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.inventory_item import InventoryItem
from app.services.equipment_lifecycle_service import (
    LIFESPAN_BY_TYPE,
    compute_capex_forecast,
    compute_replacement_timeline,
)

# ── Helpers ────────────────────────────────────────────────────────


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


async def _create_inventory_item(
    db,
    building_id,
    *,
    item_type="boiler",
    name="Boiler",
    installation_date=None,
    replacement_cost_chf=None,
):
    item = InventoryItem(
        id=uuid.uuid4(),
        building_id=building_id,
        item_type=item_type,
        name=name,
        installation_date=installation_date,
        replacement_cost_chf=replacement_cost_chf,
    )
    db.add(item)
    await db.flush()
    return item


# ── Timeline Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_building_timeline(db_session, admin_user):
    """Building with no inventory items → empty timeline."""
    building = await _create_building(db_session, admin_user)
    timeline = await compute_replacement_timeline(db_session, building.id)
    assert timeline == []


@pytest.mark.asyncio
async def test_single_item_ok(db_session, admin_user):
    """Recently installed boiler → urgency 'ok'."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="boiler",
        name="New Boiler",
        installation_date=date.today() - timedelta(days=365),  # 1 year old
        replacement_cost_chf=8000.0,
    )

    timeline = await compute_replacement_timeline(db_session, building.id)
    assert len(timeline) == 1
    entry = timeline[0]
    assert entry["item_type"] == "boiler"
    assert entry["urgency"] == "ok"
    assert entry["expected_lifespan"] == 15
    assert entry["age_years"] == pytest.approx(1.0, abs=0.2)
    assert entry["remaining_life"] == pytest.approx(14.0, abs=0.2)
    assert entry["replacement_cost"] == 8000.0


@pytest.mark.asyncio
async def test_overdue_item(db_session, admin_user):
    """Boiler installed 20 years ago (lifespan 15y) → urgency 'overdue'."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="boiler",
        name="Old Boiler",
        installation_date=date.today() - timedelta(days=365 * 20),
        replacement_cost_chf=8000.0,
    )

    timeline = await compute_replacement_timeline(db_session, building.id)
    assert len(timeline) == 1
    assert timeline[0]["urgency"] == "overdue"
    assert timeline[0]["remaining_life"] < 0


@pytest.mark.asyncio
async def test_critical_urgency(db_session, admin_user):
    """Boiler 14 years old (lifespan 15y) → remaining ~1y → 'critical'."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="boiler",
        name="Aging Boiler",
        installation_date=date.today() - timedelta(days=int(365.25 * 14)),
        replacement_cost_chf=8000.0,
    )

    timeline = await compute_replacement_timeline(db_session, building.id)
    assert timeline[0]["urgency"] == "critical"


@pytest.mark.asyncio
async def test_planned_urgency(db_session, admin_user):
    """Intercom 7 years old (lifespan 10y) → remaining ~3y → 'planned'."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="intercom",
        name="Intercom",
        installation_date=date.today() - timedelta(days=int(365.25 * 7)),
        replacement_cost_chf=3000.0,
    )

    timeline = await compute_replacement_timeline(db_session, building.id)
    assert timeline[0]["urgency"] == "planned"


@pytest.mark.asyncio
async def test_unknown_installation_date(db_session, admin_user):
    """Item without installation date → urgency 'unknown'."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="elevator",
        name="Mystery Elevator",
    )

    timeline = await compute_replacement_timeline(db_session, building.id)
    assert len(timeline) == 1
    assert timeline[0]["urgency"] == "unknown"
    assert timeline[0]["age_years"] is None
    assert timeline[0]["remaining_life"] is None


@pytest.mark.asyncio
async def test_sort_order(db_session, admin_user):
    """Multiple items sorted: overdue first, then critical, then ok."""
    building = await _create_building(db_session, admin_user)

    # Overdue boiler (20y old, lifespan 15y)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="boiler",
        name="Overdue Boiler",
        installation_date=date.today() - timedelta(days=365 * 20),
        replacement_cost_chf=8000.0,
    )
    # New elevator (1y old, lifespan 25y)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="elevator",
        name="New Elevator",
        installation_date=date.today() - timedelta(days=365),
        replacement_cost_chf=50000.0,
    )
    # Critical water heater (11y old, lifespan 12y)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="water_heater",
        name="Aging Heater",
        installation_date=date.today() - timedelta(days=int(365.25 * 11)),
        replacement_cost_chf=3000.0,
    )

    timeline = await compute_replacement_timeline(db_session, building.id)
    assert len(timeline) == 3
    assert timeline[0]["urgency"] == "overdue"
    assert timeline[1]["urgency"] == "critical"
    assert timeline[2]["urgency"] == "ok"


@pytest.mark.asyncio
async def test_all_lifespan_types_covered(db_session, admin_user):
    """All 14 item types produce valid timeline entries."""
    building = await _create_building(db_session, admin_user)
    for item_type in LIFESPAN_BY_TYPE:
        await _create_inventory_item(
            db_session,
            building.id,
            item_type=item_type,
            name=f"Test {item_type}",
            installation_date=date.today() - timedelta(days=365 * 5),
        )

    timeline = await compute_replacement_timeline(db_session, building.id)
    assert len(timeline) == 14
    types_in_result = {e["item_type"] for e in timeline}
    assert types_in_result == set(LIFESPAN_BY_TYPE.keys())


# ── CAPEX Forecast Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_capex_empty(db_session, admin_user):
    """No items → empty forecast."""
    building = await _create_building(db_session, admin_user)
    result = await compute_capex_forecast(db_session, building.id, years=10)
    assert result["forecast"] == {}
    assert result["grand_total"] == 0.0


@pytest.mark.asyncio
async def test_capex_single_item(db_session, admin_user):
    """Single overdue boiler → cost in current year."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="boiler",
        name="Overdue Boiler",
        installation_date=date.today() - timedelta(days=365 * 20),
        replacement_cost_chf=8000.0,
    )

    result = await compute_capex_forecast(db_session, building.id, years=10)
    assert result["grand_total"] == 8000.0
    assert date.today().year in result["forecast"]


@pytest.mark.asyncio
async def test_capex_item_beyond_forecast_window(db_session, admin_user):
    """Item with 20y remaining life not in 10y forecast."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="elevator",
        name="New Elevator",
        installation_date=date.today() - timedelta(days=365),
        replacement_cost_chf=50000.0,
    )

    result = await compute_capex_forecast(db_session, building.id, years=10)
    # Elevator with ~24y remaining should not be in 10y window
    assert result["grand_total"] == 0.0


@pytest.mark.asyncio
async def test_capex_missing_cost_tracked(db_session, admin_user):
    """Items without replacement_cost → counted in items_without_cost."""
    building = await _create_building(db_session, admin_user)
    await _create_inventory_item(
        db_session,
        building.id,
        item_type="boiler",
        name="Boiler No Cost",
        installation_date=date.today() - timedelta(days=365 * 20),
        # No replacement_cost_chf
    )

    result = await compute_capex_forecast(db_session, building.id, years=10)
    assert result["items_without_cost"] == 1
    assert result["grand_total"] == 0.0
