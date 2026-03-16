"""Tests for the notification rules engine."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.notification import NotificationPreferenceExtended
from app.models.organization import Organization
from app.models.user import User
from app.services.notification_rules_service import (
    ALL_TRIGGER_TYPES,
    evaluate_building_triggers,
    generate_digest,
    get_notification_preferences,
    get_org_alert_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_HASH = "$2b$12$LJ3m4ys3Lf5E5X5X5X5X5OaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaO"


def _make_user(db_session, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "email": f"u{uuid.uuid4().hex[:8]}@test.ch",
        "password_hash": _HASH,
        "first_name": "Test",
        "last_name": "User",
        "role": "admin",
        "is_active": True,
        "language": "fr",
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db_session.add(user)
    return user


def _make_building(db_session, created_by, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": created_by,
        "status": "active",
    }
    defaults.update(kwargs)
    building = Building(**defaults)
    db_session.add(building)
    return building


def _make_diagnostic(db_session, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "draft",
    }
    defaults.update(kwargs)
    diag = Diagnostic(**defaults)
    db_session.add(diag)
    return diag


# ---------------------------------------------------------------------------
# Tests — evaluate_building_triggers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_triggers_no_building(db_session):
    """Non-existent building returns empty triggers."""
    result = await evaluate_building_triggers(uuid.uuid4(), db_session)
    assert result.total == 0
    assert result.triggers == []


@pytest.mark.asyncio
async def test_triggers_clean_building(db_session):
    """Building with completed diagnostic, low risk, recent update — no triggers."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    _make_diagnostic(
        db_session,
        building.id,
        status="completed",
        date_report=datetime.now(UTC).date(),
    )
    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building.id,
        overall_risk_level="low",
    )
    db_session.add(risk)
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    assert result.total == 0


@pytest.mark.asyncio
async def test_triggers_overdue_diagnostics(db_session):
    """Draft diagnostic triggers overdue_diagnostics."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    _make_diagnostic(db_session, building.id, status="draft")
    _make_diagnostic(db_session, building.id, status="in_progress")
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    overdue = [t for t in result.triggers if t.trigger_type == "overdue_diagnostics"]
    assert len(overdue) == 2


@pytest.mark.asyncio
async def test_triggers_expiring_compliance(db_session):
    """Old completed diagnostic triggers expiring_compliance."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    old_date = (datetime.now(UTC) - timedelta(days=6 * 365)).date()
    _make_diagnostic(
        db_session,
        building.id,
        status="completed",
        date_report=old_date,
    )
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    expiring = [t for t in result.triggers if t.trigger_type == "expiring_compliance"]
    assert len(expiring) == 1
    assert expiring[0].severity == "critical"


@pytest.mark.asyncio
async def test_triggers_high_risk_unaddressed(db_session):
    """High risk + open actions triggers high_risk_unaddressed."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building.id,
        overall_risk_level="high",
    )
    db_session.add(risk)
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Fix asbestos",
        priority="high",
        status="open",
    )
    db_session.add(action)
    # Add a completed diagnostic to avoid incomplete_dossier trigger
    _make_diagnostic(db_session, building.id, status="completed")
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    high_risk = [t for t in result.triggers if t.trigger_type == "high_risk_unaddressed"]
    assert len(high_risk) == 1
    assert high_risk[0].severity == "critical"


@pytest.mark.asyncio
async def test_triggers_incomplete_dossier(db_session):
    """Building with no diagnostics triggers incomplete_dossier."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    incomplete = [t for t in result.triggers if t.trigger_type == "incomplete_dossier"]
    assert len(incomplete) == 1
    assert incomplete[0].severity == "info"


@pytest.mark.asyncio
async def test_triggers_stale_data(db_session):
    """Building not updated in 7 months triggers stale_data."""
    user = _make_user(db_session)
    stale_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=210)
    building = _make_building(
        db_session,
        created_by=user.id,
        updated_at=stale_date,
    )
    # Add a diagnostic to avoid incomplete_dossier
    _make_diagnostic(db_session, building.id, status="completed")
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    stale = [t for t in result.triggers if t.trigger_type == "stale_data"]
    assert len(stale) == 1


@pytest.mark.asyncio
async def test_triggers_all_active(db_session):
    """Building with all problems triggers all rules."""
    user = _make_user(db_session)
    stale_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=210)
    building = _make_building(db_session, created_by=user.id, updated_at=stale_date)
    # No diagnostics → incomplete_dossier + stale_data
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    types = {t.trigger_type for t in result.triggers}
    assert "incomplete_dossier" in types
    assert "stale_data" in types


@pytest.mark.asyncio
async def test_triggers_multiple_severities(db_session):
    """Triggers can have different severities."""
    user = _make_user(db_session)
    stale_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=210)
    building = _make_building(db_session, created_by=user.id, updated_at=stale_date)
    # draft diagnostic → warning, no diagnostics completed → info (incomplete doesn't fire since we have one)
    _make_diagnostic(db_session, building.id, status="draft")
    old_date = (datetime.now(UTC) - timedelta(days=6 * 365)).date()
    _make_diagnostic(db_session, building.id, status="completed", date_report=old_date)
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    severities = {t.severity for t in result.triggers}
    assert "warning" in severities  # overdue
    assert "critical" in severities  # expiring compliance


@pytest.mark.asyncio
async def test_triggers_critical_risk_also_fires(db_session):
    """Critical risk level also triggers high_risk_unaddressed."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building.id,
        overall_risk_level="critical",
    )
    db_session.add(risk)
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Fix lead",
        priority="high",
        status="open",
    )
    db_session.add(action)
    _make_diagnostic(db_session, building.id, status="completed")
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    high_risk = [t for t in result.triggers if t.trigger_type == "high_risk_unaddressed"]
    assert len(high_risk) == 1


@pytest.mark.asyncio
async def test_triggers_low_risk_no_trigger(db_session):
    """Low risk with open actions does NOT trigger high_risk_unaddressed."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building.id,
        overall_risk_level="low",
    )
    db_session.add(risk)
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Minor fix",
        priority="low",
        status="open",
    )
    db_session.add(action)
    _make_diagnostic(db_session, building.id, status="completed")
    await db_session.commit()

    result = await evaluate_building_triggers(building.id, db_session)
    high_risk = [t for t in result.triggers if t.trigger_type == "high_risk_unaddressed"]
    assert len(high_risk) == 0


# ---------------------------------------------------------------------------
# Tests — get_notification_preferences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preferences_defaults(db_session):
    """User with no saved preferences gets defaults."""
    user = _make_user(db_session)
    await db_session.commit()

    result = await get_notification_preferences(user.id, db_session)
    assert result.user_id == user.id
    assert result.enabled_triggers == ALL_TRIGGER_TYPES
    assert result.frequency == "immediate"
    assert result.channels == ["in_app"]
    assert result.quiet_hours_start is None


@pytest.mark.asyncio
async def test_preferences_custom(db_session):
    """User with saved preferences returns those."""
    user = _make_user(db_session)
    pref = NotificationPreferenceExtended(
        id=uuid.uuid4(),
        user_id=user.id,
        preferences_json=json.dumps(
            {
                "enabled_triggers": ["stale_data", "incomplete_dossier"],
                "frequency": "daily_digest",
                "channels": ["in_app", "email"],
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
            }
        ),
    )
    db_session.add(pref)
    await db_session.commit()

    result = await get_notification_preferences(user.id, db_session)
    assert result.frequency == "daily_digest"
    assert "email" in result.channels
    assert len(result.enabled_triggers) == 2
    assert result.quiet_hours_start == "22:00"


@pytest.mark.asyncio
async def test_preferences_invalid_json(db_session):
    """Invalid JSON in preferences falls back to defaults."""
    user = _make_user(db_session)
    pref = NotificationPreferenceExtended(
        id=uuid.uuid4(),
        user_id=user.id,
        preferences_json="not-json",
    )
    db_session.add(pref)
    await db_session.commit()

    result = await get_notification_preferences(user.id, db_session)
    assert result.enabled_triggers == ALL_TRIGGER_TYPES
    assert result.frequency == "immediate"


@pytest.mark.asyncio
async def test_preferences_nonexistent_user(db_session):
    """Non-existent user returns defaults."""
    result = await get_notification_preferences(uuid.uuid4(), db_session)
    assert result.enabled_triggers == ALL_TRIGGER_TYPES


# ---------------------------------------------------------------------------
# Tests — generate_digest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_digest_no_user(db_session):
    """Digest for non-existent user returns empty."""
    result = await generate_digest(uuid.uuid4(), db_session, "daily")
    assert result.total_count == 0
    assert "not found" in result.summary.lower()


@pytest.mark.asyncio
async def test_digest_no_buildings(db_session):
    """User with no buildings gets empty digest."""
    user = _make_user(db_session)
    await db_session.commit()

    result = await generate_digest(user.id, db_session, "daily")
    assert result.total_count == 0
    assert result.period == "daily"


@pytest.mark.asyncio
async def test_digest_with_triggers(db_session):
    """Digest includes triggers from user's buildings."""
    user = _make_user(db_session)
    _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    # No diagnostics -> incomplete_dossier
    await db_session.commit()

    result = await generate_digest(user.id, db_session, "daily")
    assert result.total_count > 0
    assert any(g.severity == "info" for g in result.groups)


@pytest.mark.asyncio
async def test_digest_weekly(db_session):
    """Weekly digest works."""
    user = _make_user(db_session)
    _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    await db_session.commit()

    result = await generate_digest(user.id, db_session, "weekly")
    assert result.period == "weekly"


@pytest.mark.asyncio
async def test_digest_respects_preferences(db_session):
    """Digest filters triggers based on user preferences."""
    user = _make_user(db_session)
    stale_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=210)
    _make_building(db_session, created_by=user.id, updated_at=stale_date)
    # Preferences: only stale_data enabled (not incomplete_dossier)
    pref = NotificationPreferenceExtended(
        id=uuid.uuid4(),
        user_id=user.id,
        preferences_json=json.dumps({"enabled_triggers": ["stale_data"]}),
    )
    db_session.add(pref)
    await db_session.commit()

    result = await generate_digest(user.id, db_session, "daily")
    trigger_types = {t.trigger_type for g in result.groups for t in g.items}
    assert "stale_data" in trigger_types
    assert "incomplete_dossier" not in trigger_types


@pytest.mark.asyncio
async def test_digest_groups_by_severity(db_session):
    """Digest groups triggers by severity."""
    user = _make_user(db_session)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    # draft diagnostic → warning, no completed → we need both severities
    _make_diagnostic(db_session, building.id, status="draft")
    await db_session.commit()

    result = await generate_digest(user.id, db_session, "daily")
    severities = [g.severity for g in result.groups]
    # Should have warning (overdue) and possibly info (incomplete not fired since there's a diagnostic)
    assert "warning" in severities


@pytest.mark.asyncio
async def test_digest_includes_org_buildings(db_session):
    """Digest includes buildings from other org members."""
    org = Organization(
        id=uuid.uuid4(),
        name="TestOrg",
        type="diagnostic_lab",
    )
    db_session.add(org)
    user1 = _make_user(db_session, organization_id=org.id)
    user2 = _make_user(db_session, organization_id=org.id)
    # Building created by user2, should be visible to user1's digest
    _make_building(db_session, created_by=user2.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    await db_session.commit()

    result = await generate_digest(user1.id, db_session, "daily")
    # The building from user2 should contribute triggers
    assert result.total_count > 0


# ---------------------------------------------------------------------------
# Tests — get_org_alert_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_org_summary_empty_org(db_session):
    """Org with no members returns empty summary."""
    result = await get_org_alert_summary(uuid.uuid4(), db_session)
    assert result.total_active_alerts == 0
    assert result.trend == "stable"
    assert result.top_triggered_rules == []
    assert result.buildings_with_most_alerts == []


@pytest.mark.asyncio
async def test_org_summary_no_buildings(db_session):
    """Org with members but no buildings returns zero alerts."""
    org = Organization(id=uuid.uuid4(), name="EmptyOrg", type="diagnostic_lab")
    db_session.add(org)
    _make_user(db_session, organization_id=org.id)
    await db_session.commit()

    result = await get_org_alert_summary(org.id, db_session)
    assert result.total_active_alerts == 0


@pytest.mark.asyncio
async def test_org_summary_with_alerts(db_session):
    """Org with buildings having alerts returns proper summary."""
    org = Organization(id=uuid.uuid4(), name="AlertOrg", type="property_management")
    db_session.add(org)
    user = _make_user(db_session, organization_id=org.id)
    # Building with no diagnostics → incomplete_dossier
    _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    await db_session.commit()

    result = await get_org_alert_summary(org.id, db_session)
    assert result.total_active_alerts > 0
    assert "incomplete_dossier" in result.top_triggered_rules
    assert len(result.buildings_with_most_alerts) == 1


@pytest.mark.asyncio
async def test_org_summary_multiple_buildings(db_session):
    """Org summary aggregates across multiple buildings."""
    org = Organization(id=uuid.uuid4(), name="MultiOrg", type="property_management")
    db_session.add(org)
    user = _make_user(db_session, organization_id=org.id)
    _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    # Both have no diagnostics
    await db_session.commit()

    result = await get_org_alert_summary(org.id, db_session)
    assert len(result.buildings_with_most_alerts) == 2
    assert result.by_severity.get("info", 0) >= 2  # incomplete_dossier on both


@pytest.mark.asyncio
async def test_org_summary_severity_breakdown(db_session):
    """Severity breakdown is accurate."""
    org = Organization(id=uuid.uuid4(), name="SevOrg", type="property_management")
    db_session.add(org)
    user = _make_user(db_session, organization_id=org.id)
    building = _make_building(db_session, created_by=user.id, updated_at=datetime.now(UTC).replace(tzinfo=None))
    # draft diagnostic → warning
    _make_diagnostic(db_session, building.id, status="draft")
    await db_session.commit()

    result = await get_org_alert_summary(org.id, db_session)
    assert result.by_severity.get("warning", 0) >= 1


# ---------------------------------------------------------------------------
# Tests — API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_triggers_endpoint(client, auth_headers, sample_building):
    """GET /api/v1/notification-rules/triggers/{id} returns triggers."""
    resp = await client.get(
        f"/api/v1/notification-rules/triggers/{sample_building.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "triggers" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_api_preferences_endpoint(client, auth_headers):
    """GET /api/v1/notification-rules/preferences returns preferences."""
    resp = await client.get(
        "/api/v1/notification-rules/preferences",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled_triggers" in data
    assert "frequency" in data


@pytest.mark.asyncio
async def test_api_digest_endpoint(client, auth_headers):
    """GET /api/v1/notification-rules/digest returns digest."""
    resp = await client.get(
        "/api/v1/notification-rules/digest?period=daily",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "groups" in data
    assert "total_count" in data


@pytest.mark.asyncio
async def test_api_org_summary_endpoint(client, auth_headers):
    """GET /api/v1/notification-rules/org-summary/{id} returns summary."""
    org_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/notification-rules/org-summary/{org_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_active_alerts" in data
    assert "trend" in data


@pytest.mark.asyncio
async def test_api_triggers_unauthenticated(client):
    """Unauthenticated request returns 403."""
    resp = await client.get(
        f"/api/v1/notification-rules/triggers/{uuid.uuid4()}",
    )
    assert resp.status_code == 403
