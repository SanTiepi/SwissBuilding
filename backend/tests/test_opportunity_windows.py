"""Tests for the OpportunityWindow detection service.

Covers weather, lease, maintenance, regulatory window detection,
portfolio aggregation, days_remaining computation, confidence levels,
and graceful degradation when data sources are missing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.building import Building
from app.models.climate_exposure import ClimateExposureProfile, OpportunityWindow
from app.models.inventory_item import InventoryItem
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.schemas.opportunity_window import OpportunityWindowResponse
from app.services.opportunity_window_service import (
    _lease_windows,
    _maintenance_windows,
    _permit_windows,
    _regulatory_windows,
    _subsidy_windows,
    _weather_window_from_profile,
    detect_windows,
    list_building_windows,
    list_portfolio_windows,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

ORG_ID = uuid.uuid4()


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Fenetre 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
        "organization_id": ORG_ID,
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _make_profile(db, building_id, altitude_m=None, frost_days=None, **kwargs):
    profile = ClimateExposureProfile(
        id=uuid.uuid4(),
        building_id=building_id,
        altitude_m=altitude_m,
        freeze_thaw_cycles_per_year=frost_days,
        **kwargs,
    )
    db.add(profile)
    await db.flush()
    return profile


async def _make_lease(db, building_id, user_id, date_end, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "lease_type": "residential",
        "reference_code": f"BAIL-{uuid.uuid4().hex[:6]}",
        "tenant_type": "contact",
        "tenant_id": uuid.uuid4(),
        "date_start": date(2020, 1, 1),
        "date_end": date_end,
        "status": "active",
        "created_by": user_id,
    }
    defaults.update(kwargs)
    lease = Lease(**defaults)
    db.add(lease)
    await db.flush()
    return lease


async def _make_inventory_item(db, building_id, user_id, warranty_end_date, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "item_type": "boiler",
        "name": "Chaudiere Viessmann",
        "warranty_end_date": warranty_end_date,
        "replacement_cost_chf": 12000.0,
        "created_by": user_id,
    }
    defaults.update(kwargs)
    item = InventoryItem(**defaults)
    db.add(item)
    await db.flush()
    return item


async def _make_obligation(db, building_id, due_date, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "title": "Inspection amiante obligatoire",
        "obligation_type": "regulatory_inspection",
        "due_date": due_date,
        "status": "upcoming",
        "priority": "high",
    }
    defaults.update(kwargs)
    obl = Obligation(**defaults)
    db.add(obl)
    await db.flush()
    return obl


async def _make_permit(db, building_id, expires_at, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "procedure_type": "construction_permit",
        "title": "Permis de construire",
        "status": "approved",
        "expires_at": expires_at,
    }
    defaults.update(kwargs)
    permit = PermitProcedure(**defaults)
    db.add(permit)
    await db.flush()
    return permit


def _today():
    return datetime.now(UTC).date()


# ---------------------------------------------------------------------------
# Weather window tests
# ---------------------------------------------------------------------------


class TestWeatherWindowLowland:
    """test_detect_weather_window_lowland: frost_days < 60 -> May-Sep."""

    def test_lowland_no_profile(self):
        """No profile -> defaults to lowland window."""
        today = date(2026, 3, 1)
        horizon = today + timedelta(days=365)
        windows = _weather_window_from_profile(None, today, horizon)
        assert len(windows) >= 1
        w = windows[0]
        assert w["window_type"] == "weather"
        assert "plaine" in w["title"]
        # Start should be May
        assert w["window_start"].month >= 3  # effective start is max(May, today)

    def test_lowland_low_altitude(self):
        """Altitude < 1000 and frost_days < 60 -> lowland."""
        profile = ClimateExposureProfile(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            altitude_m=500.0,
            freeze_thaw_cycles_per_year=40,
        )
        today = date(2026, 1, 15)
        horizon = today + timedelta(days=365)
        windows = _weather_window_from_profile(profile, today, horizon)
        assert len(windows) >= 1
        assert "plaine" in windows[0]["title"]
        assert windows[0]["confidence"] == 0.85


class TestWeatherWindowMountain:
    """test_detect_weather_window_mountain: altitude > 1000 -> Jun-Aug."""

    def test_mountain_high_altitude(self):
        """Altitude >= 1000 -> mountain window Jun-Aug."""
        profile = ClimateExposureProfile(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            altitude_m=1200.0,
            freeze_thaw_cycles_per_year=90,
        )
        today = date(2026, 1, 15)
        horizon = today + timedelta(days=365)
        windows = _weather_window_from_profile(profile, today, horizon)
        assert len(windows) >= 1
        w = windows[0]
        assert "montagne" in w["title"]
        assert w["confidence"] == 0.80

    def test_mountain_from_frost_days(self):
        """frost_days >= 60 with no altitude -> treated as mountain."""
        profile = ClimateExposureProfile(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            altitude_m=None,
            freeze_thaw_cycles_per_year=80,
        )
        today = date(2026, 1, 15)
        horizon = today + timedelta(days=365)
        windows = _weather_window_from_profile(profile, today, horizon)
        assert len(windows) >= 1
        assert "montagne" in windows[0]["title"]
        # Lower confidence because altitude is missing
        assert windows[0]["confidence"] == 0.60


# ---------------------------------------------------------------------------
# Lease window tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_lease_window(db, admin_user):
    """test_detect_lease_window: lease ending in 4 months."""
    building = await _make_building(db, admin_user.id)
    today = _today()
    end_date = today + timedelta(days=120)
    await _make_lease(db, building.id, admin_user.id, date_end=end_date)
    await db.commit()

    horizon = today + timedelta(days=365)
    windows = await _lease_windows(db, building.id, today, horizon)
    assert len(windows) == 1
    assert windows[0]["window_type"] == "occupancy"
    assert "renovation" in windows[0]["title"].lower()


@pytest.mark.asyncio
async def test_detect_no_lease_window(db, admin_user):
    """test_detect_no_lease_window: no lease ending soon -> no window."""
    building = await _make_building(db, admin_user.id)
    today = _today()
    # Lease ends in 2 years — outside threshold
    end_date = today + timedelta(days=730)
    await _make_lease(db, building.id, admin_user.id, date_end=end_date)
    await db.commit()

    horizon = today + timedelta(days=365)
    windows = await _lease_windows(db, building.id, today, horizon)
    assert len(windows) == 0


# ---------------------------------------------------------------------------
# Maintenance window tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_maintenance_window(db, admin_user):
    """test_detect_maintenance_window: warranty expiring in 3 months."""
    building = await _make_building(db, admin_user.id)
    today = _today()
    warranty_end = today + timedelta(days=90)
    await _make_inventory_item(db, building.id, admin_user.id, warranty_end_date=warranty_end)
    await db.commit()

    horizon = today + timedelta(days=365)
    windows = await _maintenance_windows(db, building.id, today, horizon)
    assert len(windows) == 1
    assert windows[0]["window_type"] == "maintenance"
    assert "garantie" in windows[0]["title"].lower()
    assert windows[0]["confidence"] == 0.95


# ---------------------------------------------------------------------------
# Regulatory window tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_regulatory_window(db, admin_user):
    """test_detect_regulatory_window: obligation deadline in 5 months."""
    building = await _make_building(db, admin_user.id)
    today = _today()
    due = today + timedelta(days=150)
    await _make_obligation(db, building.id, due_date=due)
    await db.commit()

    horizon = today + timedelta(days=365)
    windows = await _regulatory_windows(db, building.id, today, horizon)
    assert len(windows) == 1
    assert windows[0]["window_type"] == "regulatory"
    assert "echeance" in windows[0]["title"].lower()


# ---------------------------------------------------------------------------
# No windows detected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_windows_detected(db, admin_user):
    """test_no_windows_detected: everything OK, no urgency.

    Building has no climate profile, no leases ending, no warranties expiring,
    no obligations due. Only the default weather window should appear.
    """
    building = await _make_building(db, admin_user.id)
    await db.commit()

    # Weather window will still appear (graceful default), but no data-driven windows
    today = _today()
    horizon = today + timedelta(days=365)

    lease_w = await _lease_windows(db, building.id, today, horizon)
    maint_w = await _maintenance_windows(db, building.id, today, horizon)
    reg_w = await _regulatory_windows(db, building.id, today, horizon)

    assert len(lease_w) == 0
    assert len(maint_w) == 0
    assert len(reg_w) == 0


# ---------------------------------------------------------------------------
# Multiple windows same building
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_windows_same_building(db, admin_user):
    """test_multiple_windows_same_building: lease + maintenance + regulatory."""
    building = await _make_building(db, admin_user.id)
    today = _today()

    # Lease ending in 4 months
    await _make_lease(db, building.id, admin_user.id, date_end=today + timedelta(days=120))
    # Warranty expiring in 3 months
    await _make_inventory_item(db, building.id, admin_user.id, warranty_end_date=today + timedelta(days=90))
    # Obligation due in 5 months
    await _make_obligation(db, building.id, due_date=today + timedelta(days=150))
    await db.commit()

    created = await detect_windows(db, building.id)
    await db.commit()

    # At least 1 weather + 1 lease + 1 maintenance + 1 regulatory
    types = {w.window_type for w in created}
    assert "weather" in types
    assert "occupancy" in types  # lease windows use "occupancy" type
    assert "maintenance" in types
    assert "regulatory" in types
    assert len(created) >= 4


# ---------------------------------------------------------------------------
# Days remaining calculation
# ---------------------------------------------------------------------------


class TestDaysRemaining:
    """test_window_days_remaining_calculation."""

    def test_future_window(self):
        today = datetime.now(UTC).date()
        window_end = today + timedelta(days=30)
        resp = OpportunityWindowResponse(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            window_type="weather",
            title="Test",
            window_start=today,
            window_end=window_end,
        )
        assert resp.days_remaining == 30

    def test_past_window_zero(self):
        today = datetime.now(UTC).date()
        window_end = today - timedelta(days=5)
        resp = OpportunityWindowResponse(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            window_type="weather",
            title="Test",
            window_start=today - timedelta(days=30),
            window_end=window_end,
        )
        assert resp.days_remaining == 0

    def test_today_is_end(self):
        today = datetime.now(UTC).date()
        resp = OpportunityWindowResponse(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            window_type="weather",
            title="Test",
            window_start=today - timedelta(days=10),
            window_end=today,
        )
        assert resp.days_remaining == 0


# ---------------------------------------------------------------------------
# List building windows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_building_windows(db, admin_user):
    """test_list_building_windows: lists only active, non-expired windows."""
    building = await _make_building(db, admin_user.id)
    today = _today()

    # Active window (future end)
    active = OpportunityWindow(
        building_id=building.id,
        window_type="weather",
        title="Active window",
        window_start=today,
        window_end=today + timedelta(days=60),
        status="active",
    )
    db.add(active)

    # Expired window
    expired = OpportunityWindow(
        building_id=building.id,
        window_type="maintenance",
        title="Expired window",
        window_start=today - timedelta(days=90),
        window_end=today - timedelta(days=1),
        status="expired",
    )
    db.add(expired)

    # Dismissed window (should not appear)
    dismissed = OpportunityWindow(
        building_id=building.id,
        window_type="regulatory",
        title="Dismissed window",
        window_start=today,
        window_end=today + timedelta(days=30),
        status="dismissed",
    )
    db.add(dismissed)

    await db.commit()

    result = await list_building_windows(db, building.id)
    assert len(result) == 1
    assert result[0].title == "Active window"


# ---------------------------------------------------------------------------
# List portfolio windows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_portfolio_windows(db, admin_user):
    """test_list_portfolio_windows: org-scoped, multiple buildings."""
    org_id = ORG_ID
    b1 = await _make_building(db, admin_user.id, organization_id=org_id)
    b2 = await _make_building(db, admin_user.id, organization_id=org_id)
    # Building in different org — should not appear
    other_org = uuid.uuid4()
    b3 = await _make_building(db, admin_user.id, organization_id=other_org)

    today = _today()

    for b in (b1, b2, b3):
        w = OpportunityWindow(
            building_id=b.id,
            window_type="weather",
            title=f"Window for {b.id}",
            window_start=today,
            window_end=today + timedelta(days=60),
            status="active",
        )
        db.add(w)

    await db.commit()

    result = await list_portfolio_windows(db, org_id)
    assert len(result) == 2  # b1 + b2, not b3
    building_ids = {w.building_id for w in result}
    assert b1.id in building_ids
    assert b2.id in building_ids
    assert b3.id not in building_ids


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_levels(db, admin_user):
    """test_confidence_levels: high/medium/low based on data quality."""
    building = await _make_building(db, admin_user.id)
    today = _today()

    # Regulatory obligation -> high confidence (0.95) for regulatory_inspection
    await _make_obligation(
        db,
        building.id,
        due_date=today + timedelta(days=100),
        obligation_type="regulatory_inspection",
    )

    # Custom obligation -> medium confidence (0.85)
    await _make_obligation(
        db,
        building.id,
        due_date=today + timedelta(days=100),
        title="Revision annuelle ascenseur",
        obligation_type="custom",
    )

    await db.commit()

    horizon = today + timedelta(days=365)
    windows = await _regulatory_windows(db, building.id, today, horizon)
    assert len(windows) == 2

    # Find the regulatory_inspection one
    reg_insp = [w for w in windows if "amiante" in w["title"].lower()]
    custom = [w for w in windows if "ascenseur" in w["title"].lower()]

    assert len(reg_insp) == 1
    assert reg_insp[0]["confidence"] == 0.95

    assert len(custom) == 1
    assert custom[0]["confidence"] == 0.85


# ---------------------------------------------------------------------------
# Cost of missing estimation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_of_missing_estimation(db, admin_user):
    """test_cost_of_missing_estimation: maintenance window includes CHF cost."""
    building = await _make_building(db, admin_user.id)
    today = _today()
    warranty_end = today + timedelta(days=60)
    await _make_inventory_item(
        db,
        building.id,
        admin_user.id,
        warranty_end_date=warranty_end,
        replacement_cost_chf=25000.0,
    )
    await db.commit()

    horizon = today + timedelta(days=365)
    windows = await _maintenance_windows(db, building.id, today, horizon)
    assert len(windows) == 1
    assert "CHF" in windows[0]["cost_of_missing"]
    assert "25" in windows[0]["cost_of_missing"]  # CHF 25,000


# ---------------------------------------------------------------------------
# Expired windows excluded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_windows_excluded(db, admin_user):
    """test_expired_windows_excluded: past windows not in active list."""
    building = await _make_building(db, admin_user.id)
    today = _today()

    # Window that ended yesterday
    past = OpportunityWindow(
        building_id=building.id,
        window_type="weather",
        title="Past window",
        window_start=today - timedelta(days=90),
        window_end=today - timedelta(days=1),
        status="active",  # still marked active but end date is past
    )
    db.add(past)
    await db.commit()

    result = await list_building_windows(db, building.id)
    # Should exclude because window_end < today
    assert len(result) == 0


# ---------------------------------------------------------------------------
# Detect with no climate profile (graceful degradation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_with_no_climate_profile(db, admin_user):
    """test_detect_with_no_climate_profile: graceful degradation.

    No ClimateExposureProfile -> still detects weather windows (lowland default)
    and data-driven windows.
    """
    building = await _make_building(db, admin_user.id)
    today = _today()

    # Add a lease ending soon so we get at least one data-driven window
    await _make_lease(db, building.id, admin_user.id, date_end=today + timedelta(days=90))
    await db.commit()

    # No profile exists for this building
    profile_check = await db.execute(
        select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id)
    )
    assert profile_check.scalar_one_or_none() is None

    created = await detect_windows(db, building.id)
    await db.commit()

    # Should have at least weather (default lowland) + lease window
    types = {w.window_type for w in created}
    assert "weather" in types
    assert "occupancy" in types  # lease window
    # Weather window confidence is lower without profile
    weather_windows = [w for w in created if w.window_type == "weather"]
    assert weather_windows[0].confidence == 0.50


# ---------------------------------------------------------------------------
# Idempotent detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_idempotent(db, admin_user):
    """Running detect_windows twice does not duplicate windows."""
    building = await _make_building(db, admin_user.id)
    await db.commit()

    first = await detect_windows(db, building.id)
    await db.commit()
    first_count = len(first)
    assert first_count > 0  # at least weather

    second = await detect_windows(db, building.id)
    await db.commit()
    # Second run should create 0 new windows
    assert len(second) == 0


# ---------------------------------------------------------------------------
# Expire old windows during detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_expires_old_windows(db, admin_user):
    """detect_windows marks past active windows as expired."""
    building = await _make_building(db, admin_user.id)
    today = _today()

    # Manually insert an active window that has ended
    old = OpportunityWindow(
        building_id=building.id,
        window_type="seasonal",
        title="Old seasonal",
        window_start=today - timedelta(days=120),
        window_end=today - timedelta(days=5),
        status="active",
    )
    db.add(old)
    await db.commit()

    await detect_windows(db, building.id)
    await db.commit()

    # Check the old window is now expired
    result = await db.execute(select(OpportunityWindow).where(OpportunityWindow.id == old.id))
    refreshed = result.scalar_one()
    assert refreshed.status == "expired"
