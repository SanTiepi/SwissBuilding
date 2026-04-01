"""Tests for Proactive Alert Engine service."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.inventory_item import InventoryItem
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.proactive_alert_engine import (
    generate_alerts,
    generate_portfolio_alerts,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db, org_id=None):
    user = User(
        id=uuid.uuid4(),
        email=f"alert-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
        organization_id=org_id,
    )
    db.add(user)
    await db.commit()
    return user


async def _make_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name="AlertTest Org",
        type="property_management",
    )
    db.add(org)
    await db.commit()
    return org


async def _make_building(db, user, **kw):
    defaults = {
        "id": uuid.uuid4(),
        "address": f"Rue Alert {uuid.uuid4().hex[:4]}",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "created_by": user.id,
        "status": "active",
    }
    defaults.update(kw)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    return b


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await generate_alerts(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_no_alerts_clean_building(db_session):
    """A new building outside 1960-1990 with nothing configured -> no alerts."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user, construction_year=2020)

    alerts = await generate_alerts(db_session, building.id)
    assert isinstance(alerts, list)
    # 2020 building won't trigger missing_diagnostic (outside range)
    missing = [a for a in alerts if a["id"] == "missing_diagnostic"]
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_missing_diagnostic_1960_1990(db_session):
    """Building 1960-1990 without asbestos diagnostic triggers alert."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user, construction_year=1975)

    alerts = await generate_alerts(db_session, building.id)
    missing = [a for a in alerts if a["id"] == "missing_diagnostic"]
    assert len(missing) == 1
    assert missing[0]["urgency"] == "high"


@pytest.mark.asyncio
async def test_no_missing_diagnostic_with_existing_diag(db_session):
    """Building 1960-1990 WITH asbestos diagnostic -> no missing_diagnostic alert."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user, construction_year=1975)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()

    alerts = await generate_alerts(db_session, building.id)
    missing = [a for a in alerts if a["id"] == "missing_diagnostic"]
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_expiring_warranty(db_session):
    """Inventory item with warranty ending in 20 days triggers alert."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    item = InventoryItem(
        id=uuid.uuid4(),
        building_id=building.id,
        item_type="boiler",
        name="Chaudière Viessmann",
        warranty_end_date=date.today() + timedelta(days=20),
    )
    db_session.add(item)
    await db_session.commit()

    alerts = await generate_alerts(db_session, building.id)
    warranty = [a for a in alerts if a["id"] == "expiring_warranty"]
    assert len(warranty) == 1
    assert warranty[0]["urgency"] == "medium"
    assert "20" in warranty[0]["message"]


@pytest.mark.asyncio
async def test_no_warranty_alert_far_future(db_session):
    """Warranty 6 months away -> no alert."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    item = InventoryItem(
        id=uuid.uuid4(),
        building_id=building.id,
        item_type="elevator",
        name="Ascenseur Schindler",
        warranty_end_date=date.today() + timedelta(days=200),
    )
    db_session.add(item)
    await db_session.commit()

    alerts = await generate_alerts(db_session, building.id)
    warranty = [a for a in alerts if a["id"] == "expiring_warranty"]
    assert len(warranty) == 0


@pytest.mark.asyncio
async def test_lease_ending_renovation_window(db_session):
    """Active lease ending in 90 days triggers renovation window alert."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    lease = Lease(
        id=uuid.uuid4(),
        building_id=building.id,
        lease_type="residential",
        reference_code="L-001",
        tenant_type="contact",
        tenant_id=uuid.uuid4(),
        date_start=date(2023, 1, 1),
        date_end=date.today() + timedelta(days=90),
        status="active",
    )
    db_session.add(lease)
    await db_session.commit()

    alerts = await generate_alerts(db_session, building.id)
    lease_alerts = [a for a in alerts if a["id"] == "lease_ending_renovation"]
    assert len(lease_alerts) == 1


@pytest.mark.asyncio
async def test_climate_risk_friable_asbestos(db_session):
    """High freeze-thaw + friable asbestos -> critical climate risk alert."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
        material_state="friable",
        concentration=3.0,
        unit="%",
    )
    db_session.add(sample)
    await db_session.commit()

    alerts = await generate_alerts(
        db_session,
        building.id,
        climate_stress={"freeze_thaw": 0.8, "uv": 0.3, "moisture": 0.5},
    )
    climate = [a for a in alerts if a["id"] == "climate_risk"]
    assert len(climate) == 1
    assert climate[0]["urgency"] == "critical"


@pytest.mark.asyncio
async def test_obligation_approaching(db_session):
    """Obligation due in 45 days triggers alert."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user)

    obl = Obligation(
        id=uuid.uuid4(),
        building_id=building.id,
        title="Inspection radon annuelle",
        obligation_type="regulatory_inspection",
        due_date=date.today() + timedelta(days=45),
        status="upcoming",
        priority="high",
    )
    db_session.add(obl)
    await db_session.commit()

    alerts = await generate_alerts(db_session, building.id)
    obl_alerts = [a for a in alerts if a["id"] == "obligation_approaching"]
    assert len(obl_alerts) == 1
    assert "45" in obl_alerts[0]["message"]


@pytest.mark.asyncio
async def test_twin_building_finding(db_session):
    """Peer positive for PCB, ref untested -> twin alert."""
    user = await _make_user(db_session)
    ref = await _make_building(db_session, user, canton="VD", construction_year=1970)
    peer = await _make_building(db_session, user, canton="VD", construction_year=1972)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=peer.id,
        diagnostic_type="pcb",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-P1",
        pollutant_type="pcb",
        threshold_exceeded=True,
        risk_level="high",
        concentration=60,
        unit="mg/kg",
    )
    db_session.add(sample)
    await db_session.commit()

    alerts = await generate_alerts(db_session, ref.id)
    twin = [a for a in alerts if a["id"] == "similar_building_finding"]
    assert len(twin) >= 1
    assert any("pcb" in a["data"].get("pollutant", "") for a in twin)


@pytest.mark.asyncio
async def test_alerts_sorted_by_urgency(db_session):
    """Alerts should be sorted: critical > high > medium > low."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user, construction_year=1975)

    # Add expiring warranty (medium) + missing diagnostic (high)
    item = InventoryItem(
        id=uuid.uuid4(),
        building_id=building.id,
        item_type="hvac",
        name="HVAC unit",
        warranty_end_date=date.today() + timedelta(days=10),
    )
    db_session.add(item)
    await db_session.commit()

    alerts = await generate_alerts(db_session, building.id)
    if len(alerts) >= 2:
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(alerts) - 1):
            assert urgency_order.get(alerts[i]["urgency"], 4) <= urgency_order.get(alerts[i + 1]["urgency"], 4)


@pytest.mark.asyncio
async def test_portfolio_alerts(db_session):
    """Portfolio alerts aggregate across buildings."""
    org = await _make_org(db_session)
    user = await _make_user(db_session, org_id=org.id)

    await _make_building(db_session, user, construction_year=1975)
    await _make_building(db_session, user, construction_year=1980)

    alerts = await generate_portfolio_alerts(db_session, org.id)
    assert isinstance(alerts, list)
    # Both buildings are 1960-1990 without asbestos diag -> 2 missing_diagnostic alerts
    missing = [a for a in alerts if a["id"] == "missing_diagnostic"]
    assert len(missing) == 2
    # Each should have building context
    for a in missing:
        assert "building_id" in a
        assert "building_address" in a
