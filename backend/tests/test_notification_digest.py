"""
Tests for the Notification Digest service and API.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.change_signal import ChangeSignal
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_digest_service import (
    generate_digest,
    get_digest_preview,
    get_overdue_actions,
    get_user_building_ids,
    mark_digest_sent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(db_session: AsyncSession, **kwargs) -> User:
    defaults = {
        "id": uuid.uuid4(),
        "email": f"test-{uuid.uuid4().hex[:8]}@test.ch",
        "password_hash": "$2b$12$LJ3m4ys3uz/3C1mVAEB6MeVu8JH2bqeeSwH.1L3VXGURW2E9bJKHe",
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


def _make_building(db_session: AsyncSession, created_by: uuid.UUID, **kwargs) -> Building:
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


def _auth_headers(user: User) -> dict:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_digest_empty_user(db_session):
    """Digest for a user with no data returns empty sections."""
    user = _make_user(db_session)
    await db_session.commit()

    digest = await generate_digest(db_session, user.id, "daily")

    assert digest.user_id == user.id
    assert digest.period == "daily"
    assert len(digest.sections) == 5
    for section in digest.sections:
        assert section.count == 0
        assert section.items == []
    assert digest.metrics.total_notifications == 0
    assert digest.metrics.overdue_actions == 0


@pytest.mark.asyncio
async def test_digest_with_notifications(db_session):
    """Digest includes unread notifications from the period."""
    user = _make_user(db_session)
    await db_session.commit()

    # Create recent unread notification
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user.id,
        type="action",
        title="New action assigned",
        body="Check building report",
        status="unread",
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    db_session.add(notif)
    await db_session.commit()

    digest = await generate_digest(db_session, user.id, "daily")

    notif_section = next(s for s in digest.sections if s.title == "Recent notifications")
    assert notif_section.count == 1
    assert notif_section.items[0]["title"] == "New action assigned"
    assert digest.metrics.total_notifications == 1
    assert digest.metrics.unread_count == 1


@pytest.mark.asyncio
async def test_digest_with_overdue_actions(db_session):
    """Digest detects overdue action items."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Remove asbestos",
        priority="high",
        status="open",
        due_date=date.today() - timedelta(days=10),
        created_by=user.id,
    )
    db_session.add(action)
    await db_session.commit()

    digest = await generate_digest(db_session, user.id, "daily")

    assert digest.metrics.overdue_actions == 1

    urgent_section = next(s for s in digest.sections if s.title == "Urgent actions")
    assert urgent_section.count == 1
    assert urgent_section.items[0]["title"] == "Remove asbestos"


@pytest.mark.asyncio
async def test_digest_with_upcoming_deadlines(db_session):
    """Digest includes actions due within 30 days as deadlines."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="compliance",
        action_type="diagnostic_renewal",
        title="Renew asbestos diagnostic",
        priority="medium",
        status="open",
        due_date=date.today() + timedelta(days=15),
        created_by=user.id,
    )
    db_session.add(action)
    await db_session.commit()

    digest = await generate_digest(db_session, user.id, "daily")

    deadlines_section = next(s for s in digest.sections if s.title == "Upcoming deadlines")
    assert deadlines_section.count == 1
    assert deadlines_section.items[0]["title"] == "Renew asbestos diagnostic"
    assert digest.metrics.upcoming_deadlines == 1


@pytest.mark.asyncio
async def test_digest_preview_headline(db_session):
    """Preview generates a meaningful headline."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    # Add overdue action
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Fix PCB",
        priority="high",
        status="open",
        due_date=date.today() - timedelta(days=5),
        created_by=user.id,
    )
    db_session.add(action)

    # Add signal
    signal = ChangeSignal(
        id=uuid.uuid4(),
        building_id=building.id,
        signal_type="regulation_change",
        severity="warning",
        title="New regulation",
        detected_at=datetime.now(UTC) - timedelta(hours=3),
    )
    db_session.add(signal)
    await db_session.commit()

    preview = await get_digest_preview(db_session, user.id, "daily")

    assert preview.has_urgent is True
    assert "actions due" in preview.headline
    assert "new signals" in preview.headline
    assert preview.total_items >= 2


@pytest.mark.asyncio
async def test_digest_preview_empty(db_session):
    """Preview with no data shows no-activity headline."""
    user = _make_user(db_session)
    await db_session.commit()

    preview = await get_digest_preview(db_session, user.id, "daily")

    assert preview.headline == "No new activity"
    assert preview.has_urgent is False
    assert preview.total_items == 0


@pytest.mark.asyncio
async def test_weekly_vs_daily_period(db_session):
    """Weekly digest captures a wider window than daily."""
    user = _make_user(db_session)
    await db_session.commit()

    # Notification 3 days ago — within weekly but outside daily
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user.id,
        type="system",
        title="System update",
        body="Scheduled maintenance",
        status="unread",
        created_at=datetime.now(UTC) - timedelta(days=3),
    )
    db_session.add(notif)
    await db_session.commit()

    daily = await generate_digest(db_session, user.id, "daily")
    weekly = await generate_digest(db_session, user.id, "weekly")

    daily_notif = next(s for s in daily.sections if s.title == "Recent notifications")
    weekly_notif = next(s for s in weekly.sections if s.title == "Recent notifications")

    assert daily_notif.count == 0
    assert weekly_notif.count == 1


@pytest.mark.asyncio
async def test_mark_digest_sent(db_session):
    """mark_digest_sent marks unread notifications as read."""
    user = _make_user(db_session)
    await db_session.commit()

    notif = Notification(
        id=uuid.uuid4(),
        user_id=user.id,
        type="action",
        title="Test notification",
        status="unread",
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(notif)
    await db_session.commit()

    await mark_digest_sent(db_session, user.id, "daily")
    await db_session.refresh(notif)

    assert notif.status == "read"
    assert notif.read_at is not None


@pytest.mark.asyncio
async def test_user_building_ids_via_created_by(db_session):
    """get_user_building_ids finds buildings created by the user."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    ids = await get_user_building_ids(db_session, user.id)
    assert building.id in ids


@pytest.mark.asyncio
async def test_user_building_ids_via_assignment(db_session):
    """get_user_building_ids finds buildings assigned to the user."""
    creator = _make_user(db_session, email="creator@test.ch")
    user = _make_user(db_session, email="assigned@test.ch")
    building = _make_building(db_session, creator.id)
    await db_session.commit()

    assignment = Assignment(
        id=uuid.uuid4(),
        target_type="building",
        target_id=building.id,
        user_id=user.id,
        role="responsible",
        created_by=creator.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    ids = await get_user_building_ids(db_session, user.id)
    assert building.id in ids


@pytest.mark.asyncio
async def test_get_overdue_actions_empty(db_session):
    """get_overdue_actions returns empty list when no buildings."""
    user = _make_user(db_session)
    await db_session.commit()

    result = await get_overdue_actions(db_session, user.id)
    assert result == []


@pytest.mark.asyncio
async def test_digest_with_completed_work(db_session):
    """Digest includes completed interventions and diagnostics."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    intv = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="asbestos_removal",
        title="Asbestos removal floor 2",
        status="completed",
        created_by=user.id,
        updated_at=datetime.now(UTC) - timedelta(hours=5),
    )
    db_session.add(intv)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        updated_at=datetime.now(UTC) - timedelta(hours=3),
    )
    db_session.add(diag)
    await db_session.commit()

    digest = await generate_digest(db_session, user.id, "daily")

    completed_section = next(s for s in digest.sections if s.title == "Completed work")
    assert completed_section.count == 2


@pytest.mark.asyncio
async def test_digest_with_change_signals(db_session):
    """Digest includes change signals from the period."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    signal = ChangeSignal(
        id=uuid.uuid4(),
        building_id=building.id,
        signal_type="data_update",
        severity="info",
        title="Address updated",
        description="Building address corrected",
        detected_at=datetime.now(UTC) - timedelta(hours=6),
    )
    db_session.add(signal)
    await db_session.commit()

    digest = await generate_digest(db_session, user.id, "daily")

    signals_section = next(s for s in digest.sections if s.title == "New signals")
    assert signals_section.count == 1
    assert signals_section.items[0]["title"] == "Address updated"
    assert digest.metrics.new_signals == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_digest_requires_auth(client):
    """GET /notifications/digest returns 403 without auth."""
    resp = await client.get("/api/v1/notifications/digest")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_digest_ok(client, admin_user, auth_headers):
    """GET /notifications/digest returns 200 with valid auth."""
    resp = await client.get("/api/v1/notifications/digest", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "daily"
    assert "sections" in data
    assert "metrics" in data


@pytest.mark.asyncio
async def test_api_digest_preview(client, admin_user, auth_headers):
    """GET /notifications/digest/preview returns a preview."""
    resp = await client.get("/api/v1/notifications/digest/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "headline" in data
    assert "has_urgent" in data


@pytest.mark.asyncio
async def test_api_mark_sent(client, admin_user, auth_headers):
    """POST /notifications/digest/mark-sent returns 200."""
    resp = await client.post("/api/v1/notifications/digest/mark-sent", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_api_digest_weekly_param(client, admin_user, auth_headers):
    """GET /notifications/digest?period=weekly returns weekly digest."""
    resp = await client.get("/api/v1/notifications/digest?period=weekly", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["period"] == "weekly"


@pytest.mark.asyncio
async def test_api_digest_invalid_period(client, admin_user, auth_headers):
    """GET /notifications/digest?period=monthly returns 422."""
    resp = await client.get("/api/v1/notifications/digest?period=monthly", headers=auth_headers)
    assert resp.status_code == 422
