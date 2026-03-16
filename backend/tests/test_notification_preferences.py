"""Tests for extended notification preferences: channel routing, quiet hours, per-type granularity."""

import pytest

from app.schemas.notification_preferences import (
    NotificationPreferencesUpdate,
    NotificationTypePreference,
    QuietHours,
)
from app.services import notification_preferences_service as svc

# ---------------------------------------------------------------------------
# Service-level tests (direct DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_preferences_created(db_session, admin_user):
    """First call creates defaults: all types enabled for in_app, quiet hours off, digest=never."""
    prefs = await svc.get_full_preferences(db_session, admin_user.id)
    assert prefs.user_id == admin_user.id
    assert len(prefs.type_preferences) == 4
    assert prefs.quiet_hours.enabled is False
    assert prefs.digest_frequency == "never"
    for tp in prefs.type_preferences:
        assert tp.enabled is True
        assert tp.channels == ["in_app"]


@pytest.mark.asyncio
async def test_get_preferences_idempotent(db_session, admin_user):
    """Calling get twice returns the same data (no duplicate rows)."""
    p1 = await svc.get_full_preferences(db_session, admin_user.id)
    p2 = await svc.get_full_preferences(db_session, admin_user.id)
    assert p1.user_id == p2.user_id
    assert len(p1.type_preferences) == len(p2.type_preferences)


@pytest.mark.asyncio
async def test_update_digest_frequency(db_session, admin_user):
    """Partial update of digest_frequency preserves other fields."""
    await svc.get_full_preferences(db_session, admin_user.id)
    updated = await svc.update_preferences(
        db_session, admin_user.id, NotificationPreferencesUpdate(digest_frequency="daily")
    )
    assert updated.digest_frequency == "daily"
    assert len(updated.type_preferences) == 4  # preserved


@pytest.mark.asyncio
async def test_update_quiet_hours(db_session, admin_user):
    """Update quiet hours only."""
    await svc.get_full_preferences(db_session, admin_user.id)
    qh = QuietHours(enabled=True, start_hour=23, end_hour=6, timezone="Europe/Zurich")
    updated = await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(quiet_hours=qh))
    assert updated.quiet_hours.enabled is True
    assert updated.quiet_hours.start_hour == 23
    assert updated.quiet_hours.end_hour == 6


@pytest.mark.asyncio
async def test_update_type_preferences(db_session, admin_user):
    """Replace type_preferences entirely."""
    await svc.get_full_preferences(db_session, admin_user.id)
    new_tp = [
        NotificationTypePreference(type="action", channels=["in_app", "email"], enabled=True),
        NotificationTypePreference(type="invitation", channels=["in_app"], enabled=False),
    ]
    updated = await svc.update_preferences(
        db_session, admin_user.id, NotificationPreferencesUpdate(type_preferences=new_tp)
    )
    assert len(updated.type_preferences) == 2
    action_pref = next(tp for tp in updated.type_preferences if tp.type == "action")
    assert "email" in action_pref.channels
    inv_pref = next(tp for tp in updated.type_preferences if tp.type == "invitation")
    assert inv_pref.enabled is False


@pytest.mark.asyncio
async def test_partial_update_preserves_existing(db_session, admin_user):
    """Updating one field does not reset others."""
    await svc.get_full_preferences(db_session, admin_user.id)
    await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(digest_frequency="weekly"))
    # Now update quiet hours only
    qh = QuietHours(enabled=True, start_hour=20, end_hour=8)
    result = await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(quiet_hours=qh))
    assert result.digest_frequency == "weekly"  # preserved
    assert result.quiet_hours.enabled is True


@pytest.mark.asyncio
async def test_should_notify_default_in_app(db_session, admin_user):
    """By default, in_app notifications for all types should be allowed."""
    assert await svc.should_notify(db_session, admin_user.id, "action", "in_app") is True
    assert await svc.should_notify(db_session, admin_user.id, "system", "in_app") is True


@pytest.mark.asyncio
async def test_should_notify_disabled_type(db_session, admin_user):
    """Disabled type should not notify."""
    new_tp = [NotificationTypePreference(type="action", channels=["in_app"], enabled=False)]
    await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(type_preferences=new_tp))
    assert await svc.should_notify(db_session, admin_user.id, "action", "in_app") is False


@pytest.mark.asyncio
async def test_should_notify_wrong_channel(db_session, admin_user):
    """Channel not listed should not notify."""
    assert await svc.should_notify(db_session, admin_user.id, "action", "email") is False


@pytest.mark.asyncio
async def test_should_notify_unknown_type(db_session, admin_user):
    """Unknown notification type should not notify."""
    assert await svc.should_notify(db_session, admin_user.id, "nonexistent", "in_app") is False


@pytest.mark.asyncio
async def test_quiet_hours_blocks_during_window(db_session, admin_user):
    """Notifications blocked during quiet hours (overnight wrap)."""
    qh = QuietHours(enabled=True, start_hour=22, end_hour=7)
    await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(quiet_hours=qh))
    # 23:00 is inside quiet hours (22-7 wraps)
    assert await svc.should_notify(db_session, admin_user.id, "action", "in_app", now_hour=23) is False
    # 3:00 is inside quiet hours
    assert await svc.should_notify(db_session, admin_user.id, "action", "in_app", now_hour=3) is False


@pytest.mark.asyncio
async def test_quiet_hours_allows_outside_window(db_session, admin_user):
    """Notifications allowed outside quiet hours."""
    qh = QuietHours(enabled=True, start_hour=22, end_hour=7)
    await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(quiet_hours=qh))
    # 10:00 is outside quiet hours
    assert await svc.should_notify(db_session, admin_user.id, "action", "in_app", now_hour=10) is True


@pytest.mark.asyncio
async def test_system_bypasses_quiet_hours(db_session, admin_user):
    """System notifications always delivered, even during quiet hours."""
    qh = QuietHours(enabled=True, start_hour=22, end_hour=7)
    new_tp = [
        NotificationTypePreference(type="system", channels=["in_app"], enabled=True),
    ]
    await svc.update_preferences(
        db_session,
        admin_user.id,
        NotificationPreferencesUpdate(quiet_hours=qh, type_preferences=new_tp),
    )
    assert await svc.should_notify(db_session, admin_user.id, "system", "in_app", now_hour=23) is True


@pytest.mark.asyncio
async def test_quiet_hours_daytime_range(db_session, admin_user):
    """Quiet hours that don't wrap midnight (e.g. 9-17)."""
    qh = QuietHours(enabled=True, start_hour=9, end_hour=17)
    await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(quiet_hours=qh))
    assert await svc.should_notify(db_session, admin_user.id, "action", "in_app", now_hour=12) is False
    assert await svc.should_notify(db_session, admin_user.id, "action", "in_app", now_hour=20) is True


@pytest.mark.asyncio
async def test_digest_candidates(db_session, admin_user, diagnostician_user):
    """Only users with daily/weekly digest show as candidates."""
    await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(digest_frequency="daily"))
    await svc.get_full_preferences(db_session, diagnostician_user.id)  # default = never

    candidates = await svc.get_digest_candidates(db_session)
    assert admin_user.id in candidates
    assert diagnostician_user.id not in candidates


@pytest.mark.asyncio
async def test_digest_candidates_weekly(db_session, admin_user):
    """Weekly digest users are also candidates."""
    await svc.update_preferences(db_session, admin_user.id, NotificationPreferencesUpdate(digest_frequency="weekly"))
    candidates = await svc.get_digest_candidates(db_session)
    assert admin_user.id in candidates


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_get_full_preferences(client, admin_user, auth_headers):
    resp = await client.get("/api/v1/notifications/preferences/full", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(admin_user.id)
    assert len(data["type_preferences"]) == 4
    assert data["quiet_hours"]["enabled"] is False
    assert data["digest_frequency"] == "never"


@pytest.mark.asyncio
async def test_api_update_full_preferences(client, admin_user, auth_headers):
    payload = {"digest_frequency": "daily", "quiet_hours": {"enabled": True, "start_hour": 21, "end_hour": 6}}
    resp = await client.put("/api/v1/notifications/preferences/full", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["digest_frequency"] == "daily"
    assert data["quiet_hours"]["enabled"] is True
    assert data["quiet_hours"]["start_hour"] == 21


@pytest.mark.asyncio
async def test_api_should_notify(client, admin_user, auth_headers):
    resp = await client.get(
        "/api/v1/notifications/preferences/should-notify?type=action&channel=in_app", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_notify"] is True


@pytest.mark.asyncio
async def test_api_should_notify_wrong_channel(client, admin_user, auth_headers):
    resp = await client.get(
        "/api/v1/notifications/preferences/should-notify?type=action&channel=email", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["should_notify"] is False
