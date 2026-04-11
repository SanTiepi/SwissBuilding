"""Tests for DefectShield — alert service: notification triggers for defect timelines.

Covers:
- State transitions trigger alert checks
- Alerts fired when deadline within 7 days (warning)
- Alerts fired when deadline has passed (critical)
- Notification includes building_id, defect_type, deadline_date
- Alert respects user notification preferences (DND)
- Deduplication prevents duplicate alerts
- scan_approaching_deadlines and scan_and_expire
"""

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.models.defect_timeline import DefectTimeline
from app.schemas.defect_timeline import DefectTimelineCreate
from app.services.defect_alert_service import (
    ALERT_TYPE_DEADLINE_APPROACHING,
    ALERT_TYPE_DEADLINE_MISSED,
    ALERT_TYPE_DEFECT_RESOLVED,
    APPROACHING_THRESHOLD_DAYS,
    _build_details,
    _make_fingerprint,
    check_deadline_on_create,
    on_status_change,
    scan_and_expire,
    scan_approaching_deadlines,
)
from app.services.defect_timeline_service import create_timeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Midi 10, 1003 Lausanne",
        "postal_code": "1003",
        "city": "Lausanne",
        "canton": "VD",
        "egid": 123456,
        "construction_year": 1975,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_timeline(db, building_id, *, discovery_date=None, status="active", **kwargs):
    """Create a DefectTimeline via the service."""
    if discovery_date is None:
        discovery_date = date.today() - timedelta(days=55)  # 5 days left
    data = DefectTimelineCreate(
        building_id=building_id,
        defect_type="construction",
        description="Fissure dans la dalle",
        discovery_date=discovery_date,
    )
    timeline = await create_timeline(db, data)
    if status != "active":
        timeline.status = status
        await db.commit()
        await db.refresh(timeline)
    for key, value in kwargs.items():
        if hasattr(timeline, key):
            setattr(timeline, key, value)
    if kwargs:
        await db.commit()
        await db.refresh(timeline)
    return timeline


# ---------------------------------------------------------------------------
# Unit tests — pure functions
# ---------------------------------------------------------------------------


class TestConstants:
    def test_approaching_threshold_is_7_days(self):
        assert APPROACHING_THRESHOLD_DAYS == 7

    def test_fingerprint_format(self):
        uid = uuid.uuid4()
        fp = _make_fingerprint("defect_deadline_approaching", uid)
        assert fp == f"defect:defect_deadline_approaching:{uid}"


class TestBuildDetails:
    def test_includes_building_id_defect_type_deadline(self):
        timeline = DefectTimeline(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            defect_type="pollutant",
            notification_deadline=date(2026, 5, 1),
            status="active",
        )
        details = _build_details(timeline)
        assert details["building_id"] == str(timeline.building_id)
        assert details["defect_type"] == "pollutant"
        assert details["deadline_date"] == "2026-05-01"

    def test_includes_days_remaining_when_provided(self):
        timeline = DefectTimeline(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            defect_type="construction",
            notification_deadline=date(2026, 5, 1),
            status="active",
        )
        details = _build_details(timeline, days_remaining=3)
        assert details["days_remaining"] == 3

    def test_omits_days_remaining_when_not_provided(self):
        timeline = DefectTimeline(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            defect_type="construction",
            notification_deadline=date(2026, 5, 1),
            status="active",
        )
        details = _build_details(timeline)
        assert "days_remaining" not in details


# ---------------------------------------------------------------------------
# Integration tests — on_status_change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOnStatusChange:
    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_expired_creates_deadline_missed_alert(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        notification = await on_status_change(db_session, timeline, "expired", admin_user.id)
        await db_session.flush()

        assert notification is not None
        assert ALERT_TYPE_DEADLINE_MISSED in notification.link
        assert "depasse" in notification.title
        assert "Art. 367 CO" in notification.body

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_resolved_creates_resolved_alert(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        notification = await on_status_change(db_session, timeline, "resolved", admin_user.id)
        await db_session.flush()

        assert notification is not None
        assert ALERT_TYPE_DEFECT_RESOLVED in notification.link
        assert "resolu" in notification.title

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_notified_does_not_trigger_alert(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        notification = await on_status_change(db_session, timeline, "notified", admin_user.id)
        assert notification is None

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_deduplication_prevents_second_alert(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        n1 = await on_status_change(db_session, timeline, "expired", admin_user.id)
        await db_session.flush()
        assert n1 is not None

        # Second call with same type+defect should be deduplicated
        n2 = await on_status_change(db_session, timeline, "expired", admin_user.id)
        assert n2 is None


# ---------------------------------------------------------------------------
# Integration tests — check_deadline_on_create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCheckDeadlineOnCreate:
    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_approaching_deadline_within_7_days_fires_warning(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        # Discovery 55 days ago → 5 days remaining (within 7-day threshold)
        timeline = await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=55))

        notification = await check_deadline_on_create(db_session, timeline, admin_user.id)
        await db_session.flush()

        assert notification is not None
        assert ALERT_TYPE_DEADLINE_APPROACHING in notification.link
        assert "jour(s)" in notification.title

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_passed_deadline_fires_critical(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        # Discovery 70 days ago → deadline passed
        timeline = await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=70))

        notification = await check_deadline_on_create(db_session, timeline, admin_user.id)
        await db_session.flush()

        assert notification is not None
        assert ALERT_TYPE_DEADLINE_MISSED in notification.link
        assert "depasse" in notification.title

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_far_deadline_no_alert(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        # Discovery 10 days ago → 50 days remaining (well beyond 7-day threshold)
        timeline = await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=10))

        notification = await check_deadline_on_create(db_session, timeline, admin_user.id)
        assert notification is None


# ---------------------------------------------------------------------------
# Integration tests — scan_approaching_deadlines
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScanApproachingDeadlines:
    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_picks_up_defects_within_threshold(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        # 3 days remaining
        await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=57))
        # 30 days remaining — outside threshold
        await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=30))

        created = await scan_approaching_deadlines(db_session, admin_user.id)
        assert len(created) == 1
        assert ALERT_TYPE_DEADLINE_APPROACHING in created[0].link

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_filters_by_building_id(self, mock_notify, db_session, admin_user):
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, egid=999999)
        await _make_timeline(db_session, b1.id, discovery_date=date.today() - timedelta(days=57))
        await _make_timeline(db_session, b2.id, discovery_date=date.today() - timedelta(days=57))

        created = await scan_approaching_deadlines(db_session, admin_user.id, building_id=b1.id)
        assert len(created) == 1


# ---------------------------------------------------------------------------
# Integration tests — scan_and_expire
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScanAndExpire:
    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_marks_expired_and_creates_alert(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        # 70 days ago → deadline has passed
        timeline = await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=70))

        created = await scan_and_expire(db_session, admin_user.id)
        assert len(created) == 1
        assert ALERT_TYPE_DEADLINE_MISSED in created[0].link

        # Timeline should now be expired
        await db_session.refresh(timeline)
        assert timeline.status == "expired"

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_ignores_non_active_timelines(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        # Already notified — should not be picked up
        await _make_timeline(
            db_session,
            building.id,
            discovery_date=date.today() - timedelta(days=70),
            status="notified",
        )

        created = await scan_and_expire(db_session, admin_user.id)
        assert len(created) == 0


# ---------------------------------------------------------------------------
# Integration tests — notification preferences respected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPreferencesRespected:
    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=False)
    async def test_alert_blocked_when_preferences_deny(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        notification = await on_status_change(db_session, timeline, "expired", admin_user.id)
        assert notification is None

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=False)
    async def test_scan_respects_preferences(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=57))

        created = await scan_approaching_deadlines(db_session, admin_user.id)
        assert len(created) == 0

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=False)
    async def test_check_on_create_respects_preferences(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=55))

        notification = await check_deadline_on_create(db_session, timeline, admin_user.id)
        assert notification is None


# ---------------------------------------------------------------------------
# Integration tests — notification content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNotificationContent:
    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_expired_alert_includes_building_defect_deadline(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        notification = await on_status_change(db_session, timeline, "expired", admin_user.id)
        await db_session.flush()

        assert notification is not None
        assert timeline.defect_type in notification.title
        assert timeline.notification_deadline.isoformat() in notification.body
        assert "Art. 367 CO" in notification.body

    @patch("app.services.defect_alert_service._should_notify_user", new_callable=AsyncMock, return_value=True)
    async def test_approaching_alert_includes_days_remaining(self, mock_notify, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id, discovery_date=date.today() - timedelta(days=55))

        notification = await check_deadline_on_create(db_session, timeline, admin_user.id)
        await db_session.flush()

        assert notification is not None
        assert "jour(s) restant(s)" in notification.body
        assert timeline.notification_deadline.isoformat() in notification.body
