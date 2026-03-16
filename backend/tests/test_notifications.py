import uuid

import pytest

from app.models.notification import Notification, NotificationPreference

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_notification(db, user_id, type_="action", title="Test", status="unread", **kwargs):
    n = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type=type_,
        title=title,
        status=status,
        **kwargs,
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


# ---------------------------------------------------------------------------
# GET /notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_notifications_empty(client, admin_user, auth_headers):
    resp = await client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_notifications_with_data(client, admin_user, auth_headers, db_session):
    await _make_notification(db_session, admin_user.id, title="Notif 1")
    await _make_notification(db_session, admin_user.id, title="Notif 2")

    resp = await client.get("/api/v1/notifications", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_notifications_filter_by_status(client, admin_user, auth_headers, db_session):
    await _make_notification(db_session, admin_user.id, title="Unread", status="unread")
    await _make_notification(db_session, admin_user.id, title="Read", status="read")

    resp = await client.get("/api/v1/notifications?status=unread", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Unread"


@pytest.mark.asyncio
async def test_list_notifications_user_isolation(client, admin_user, auth_headers, db_session, diagnostician_user):
    """Users should only see their own notifications."""
    await _make_notification(db_session, admin_user.id, title="Admin notif")
    await _make_notification(db_session, diagnostician_user.id, title="Diag notif")

    resp = await client.get("/api/v1/notifications", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Admin notif"


# ---------------------------------------------------------------------------
# PUT /notifications/{id}/read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_notification_read(client, admin_user, auth_headers, db_session):
    n = await _make_notification(db_session, admin_user.id)

    resp = await client.put(f"/api/v1/notifications/{n.id}/read", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "read"
    assert data["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_notification_read_not_found(client, admin_user, auth_headers):
    resp = await client.put(f"/api/v1/notifications/{uuid.uuid4()}/read", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_notification_read_other_user(client, admin_user, auth_headers, db_session, diagnostician_user):
    """Cannot mark another user's notification as read."""
    n = await _make_notification(db_session, diagnostician_user.id)
    resp = await client.put(f"/api/v1/notifications/{n.id}/read", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /notifications/read-all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_all_read(client, admin_user, auth_headers, db_session):
    await _make_notification(db_session, admin_user.id, title="N1")
    await _make_notification(db_session, admin_user.id, title="N2")
    await _make_notification(db_session, admin_user.id, title="N3", status="read")

    resp = await client.put("/api/v1/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2

    # Verify all are read now
    resp2 = await client.get("/api/v1/notifications?status=unread", headers=auth_headers)
    assert resp2.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /notifications/unread-count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unread_count(client, admin_user, auth_headers, db_session):
    await _make_notification(db_session, admin_user.id, title="N1")
    await _make_notification(db_session, admin_user.id, title="N2")
    await _make_notification(db_session, admin_user.id, title="N3", status="read")

    resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


@pytest.mark.asyncio
async def test_unread_count_user_isolation(client, admin_user, auth_headers, db_session, diagnostician_user):
    await _make_notification(db_session, admin_user.id)
    await _make_notification(db_session, diagnostician_user.id)

    resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.json()["count"] == 1


# ---------------------------------------------------------------------------
# GET /notifications/preferences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_preferences_creates_default(client, admin_user, auth_headers):
    resp = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["in_app_actions"] is True
    assert data["in_app_invitations"] is True
    assert data["in_app_exports"] is True
    assert data["digest_enabled"] is False


@pytest.mark.asyncio
async def test_get_preferences_returns_existing(client, admin_user, auth_headers, db_session):
    pref = NotificationPreference(
        id=uuid.uuid4(),
        user_id=admin_user.id,
        in_app_actions=False,
        digest_enabled=True,
    )
    db_session.add(pref)
    await db_session.commit()

    resp = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
    data = resp.json()
    assert data["in_app_actions"] is False
    assert data["digest_enabled"] is True


# ---------------------------------------------------------------------------
# PUT /notifications/preferences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_preferences(client, admin_user, auth_headers):
    resp = await client.put(
        "/api/v1/notifications/preferences",
        json={"digest_enabled": True, "in_app_exports": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["digest_enabled"] is True
    assert data["in_app_exports"] is False
    # Defaults preserved
    assert data["in_app_actions"] is True


@pytest.mark.asyncio
async def test_update_preferences_partial(client, admin_user, auth_headers):
    """Partial update should only change specified fields."""
    # First set everything
    await client.put(
        "/api/v1/notifications/preferences",
        json={"in_app_actions": False, "in_app_invitations": False, "in_app_exports": False, "digest_enabled": True},
        headers=auth_headers,
    )
    # Then update only one field
    resp = await client.put(
        "/api/v1/notifications/preferences",
        json={"in_app_actions": True},
        headers=auth_headers,
    )
    data = resp.json()
    assert data["in_app_actions"] is True
    assert data["in_app_invitations"] is False  # unchanged
    assert data["digest_enabled"] is True  # unchanged
