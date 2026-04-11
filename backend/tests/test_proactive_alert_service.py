"""Tests for the proactive alert service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.services.proactive_alert_service import (
    get_alert_summary,
    scan_and_alert,
    scan_portfolio_alerts,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, org_id=None):
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
        organization_id=org_id or admin_user.organization_id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_action(db, building_id, priority="critical", status="open", days_ago=60):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        title="Action urgente test",
        description="Test action",
        source_type="diagnostic",
        action_type="remediation",
        priority=priority,
        status=status,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )
    db.add(a)
    await db.flush()
    return a


async def _create_diagnostic(db, building_id, status="completed"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="avant_travaux",
        status=status,
    )
    db.add(d)
    await db.flush()
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_detects_overdue_critical_action(db_session, admin_user):
    """Critical action open > 30 days should trigger an alert."""
    building = await _create_building(db_session, admin_user)
    await _create_action(db_session, building.id, priority="critical", days_ago=45)

    alerts = await scan_and_alert(db_session, building.id, admin_user.id)

    overdue = [a for a in alerts if a["alert_type"] == "overdue_action"]
    assert len(overdue) >= 1
    assert overdue[0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_scan_detects_stale_building(db_session, admin_user):
    """Building with no recent activity should trigger stale alert."""
    building = await _create_building(db_session, admin_user)
    # No diagnostics, documents, or actions = stale

    alerts = await scan_and_alert(db_session, building.id, admin_user.id)

    stale = [a for a in alerts if a["alert_type"] == "stale_building"]
    assert len(stale) >= 1


@pytest.mark.asyncio
async def test_deduplication_prevents_duplicate_alerts(db_session, admin_user):
    """Same alert type + building + entity should not be duplicated."""
    building = await _create_building(db_session, admin_user)
    await _create_action(db_session, building.id, priority="critical", days_ago=45)

    # First scan
    alerts1 = await scan_and_alert(db_session, building.id, admin_user.id)
    await db_session.flush()

    # Second scan — same conditions, should deduplicate
    alerts2 = await scan_and_alert(db_session, building.id, admin_user.id)

    # The overdue_action alert should only appear in the first scan
    overdue1 = [a for a in alerts1 if a["alert_type"] == "overdue_action"]
    overdue2 = [a for a in alerts2 if a["alert_type"] == "overdue_action"]
    assert len(overdue1) >= 1
    assert len(overdue2) == 0


@pytest.mark.asyncio
async def test_portfolio_scan_aggregation(db_session, admin_user):
    """Portfolio scan should aggregate alerts across buildings."""
    org_id = admin_user.organization_id
    b1 = await _create_building(db_session, admin_user, org_id=org_id)
    b2 = await _create_building(db_session, admin_user, org_id=org_id)
    await _create_action(db_session, b1.id, priority="critical", days_ago=45)
    await _create_action(db_session, b2.id, priority="critical", days_ago=45)

    alerts = await scan_portfolio_alerts(db_session, org_id, admin_user.id)

    # Should have alerts from both buildings
    building_ids = {a["building_id"] for a in alerts if a.get("building_id") != "portfolio"}
    assert str(b1.id) in building_ids
    assert str(b2.id) in building_ids


@pytest.mark.asyncio
async def test_alert_summary_counts(db_session, admin_user):
    """Summary should count alerts by severity and type."""
    org_id = admin_user.organization_id
    building = await _create_building(db_session, admin_user, org_id=org_id)
    await _create_action(db_session, building.id, priority="critical", days_ago=45)

    # Generate alerts first
    await scan_and_alert(db_session, building.id, admin_user.id)
    await db_session.flush()

    summary = await get_alert_summary(db_session, org_id, admin_user.id)

    assert summary["total_alerts"] >= 1
    assert isinstance(summary["by_severity"], dict)
    assert isinstance(summary["by_type"], dict)
    assert isinstance(summary["buildings_with_alerts"], int)
