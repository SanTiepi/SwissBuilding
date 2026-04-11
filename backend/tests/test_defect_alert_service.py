"""Tests for DefectShield — alert notification triggers.

Covers:
- on_status_change: expired → missed-deadline alert, resolved → resolved alert
- scan_approaching_deadlines: creates alerts for deadlines within threshold
- scan_and_expire: detects + marks expired + creates alerts
- Deduplication: no duplicate unread notifications
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.defect_timeline import DefectTimeline
from app.services.defect_alert_service import (
    ALERT_TYPE_DEADLINE_APPROACHING,
    ALERT_TYPE_DEADLINE_MISSED,
    ALERT_TYPE_DEFECT_RESOLVED,
    _make_fingerprint,
    on_status_change,
    scan_and_expire,
    scan_approaching_deadlines,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue des Alertes 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
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


async def _make_timeline(db, building_id, **kwargs):
    """Create a DefectTimeline directly (bypassing service for test control)."""
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "defect_type": "construction",
        "discovery_date": date.today() - timedelta(days=50),
        "notification_deadline": date.today() + timedelta(days=10),
        "guarantee_type": "standard",
        "status": "active",
    }
    defaults.update(kwargs)
    t = DefectTimeline(**defaults)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# on_status_change tests
# ---------------------------------------------------------------------------


class TestOnStatusChange:
    @pytest.mark.asyncio
    async def test_expired_creates_missed_deadline_alert(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=1),
        )

        notification = await on_status_change(db_session, timeline, "expired", admin_user.id)

        assert notification is not None
        assert ALERT_TYPE_DEADLINE_MISSED in notification.link
        assert "depasse" in notification.title

    @pytest.mark.asyncio
    async def test_resolved_creates_resolved_alert(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id, status="notified")

        notification = await on_status_change(db_session, timeline, "resolved", admin_user.id)

        assert notification is not None
        assert ALERT_TYPE_DEFECT_RESOLVED in notification.link
        assert "resolu" in notification.title

    @pytest.mark.asyncio
    async def test_notified_status_no_alert(self, db_session, admin_user):
        """Transitioning to 'notified' should not create an alert."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        notification = await on_status_change(db_session, timeline, "notified", admin_user.id)

        assert notification is None

    @pytest.mark.asyncio
    async def test_active_status_no_alert(self, db_session, admin_user):
        """Non-trigger statuses should not create alerts."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(db_session, building.id)

        notification = await on_status_change(db_session, timeline, "active", admin_user.id)

        assert notification is None


# ---------------------------------------------------------------------------
# Deduplication tests
# ---------------------------------------------------------------------------


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_expired_not_created(self, db_session, admin_user):
        """Same alert should not be duplicated if first is still unread."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=1),
        )

        first = await on_status_change(db_session, timeline, "expired", admin_user.id)
        await db_session.commit()

        second = await on_status_change(db_session, timeline, "expired", admin_user.id)

        assert first is not None
        assert second is None  # deduplicated

    @pytest.mark.asyncio
    async def test_duplicate_allowed_after_read(self, db_session, admin_user):
        """After marking notification as read, a new one should be created."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=1),
        )

        first = await on_status_change(db_session, timeline, "expired", admin_user.id)
        assert first is not None
        first.status = "read"
        await db_session.commit()

        second = await on_status_change(db_session, timeline, "expired", admin_user.id)
        assert second is not None  # new notification after read

    @pytest.mark.asyncio
    async def test_different_defects_not_deduplicated(self, db_session, admin_user):
        """Different defect IDs should each get their own notification."""
        building = await _make_building(db_session, admin_user.id)
        t1 = await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=1),
        )
        t2 = await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=2),
        )

        n1 = await on_status_change(db_session, t1, "expired", admin_user.id)
        n2 = await on_status_change(db_session, t2, "expired", admin_user.id)

        assert n1 is not None
        assert n2 is not None


# ---------------------------------------------------------------------------
# scan_approaching_deadlines tests
# ---------------------------------------------------------------------------


class TestScanApproachingDeadlines:
    @pytest.mark.asyncio
    async def test_approaching_within_threshold(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() + timedelta(days=7),
        )

        created = await scan_approaching_deadlines(db_session, admin_user.id)

        assert len(created) == 1
        assert ALERT_TYPE_DEADLINE_APPROACHING in created[0].link

    @pytest.mark.asyncio
    async def test_not_approaching_outside_threshold(self, db_session, admin_user):
        """Deadline > threshold_days away should not trigger."""
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() + timedelta(days=30),
        )

        created = await scan_approaching_deadlines(db_session, admin_user.id, threshold_days=14)

        assert len(created) == 0

    @pytest.mark.asyncio
    async def test_multiple_approaching(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() + timedelta(days=3),
        )
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() + timedelta(days=10),
            defect_type="pollutant",
        )

        created = await scan_approaching_deadlines(db_session, admin_user.id)

        assert len(created) == 2

    @pytest.mark.asyncio
    async def test_filter_by_building(self, db_session, admin_user):
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            b1.id,
            notification_deadline=date.today() + timedelta(days=5),
        )
        await _make_timeline(
            db_session,
            b2.id,
            notification_deadline=date.today() + timedelta(days=5),
        )

        created = await scan_approaching_deadlines(db_session, admin_user.id, building_id=b1.id)

        assert len(created) == 1

    @pytest.mark.asyncio
    async def test_skip_non_active_status(self, db_session, admin_user):
        """Only active timelines should trigger approaching alerts."""
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() + timedelta(days=5),
            status="notified",
        )

        created = await scan_approaching_deadlines(db_session, admin_user.id)

        assert len(created) == 0

    @pytest.mark.asyncio
    async def test_custom_threshold(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() + timedelta(days=25),
        )

        # Default 14 days — should not fire
        created_14 = await scan_approaching_deadlines(db_session, admin_user.id, threshold_days=14)
        assert len(created_14) == 0

        # 30 days — should fire
        created_30 = await scan_approaching_deadlines(db_session, admin_user.id, threshold_days=30)
        assert len(created_30) == 1


# ---------------------------------------------------------------------------
# scan_and_expire tests
# ---------------------------------------------------------------------------


class TestScanAndExpire:
    @pytest.mark.asyncio
    async def test_expire_and_alert(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=3),
        )

        notifications = await scan_and_expire(db_session, admin_user.id)

        assert len(notifications) == 1
        assert ALERT_TYPE_DEADLINE_MISSED in notifications[0].link

        # Verify timeline status changed
        await db_session.refresh(timeline)
        assert timeline.status == "expired"

    @pytest.mark.asyncio
    async def test_no_expire_when_future_deadline(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() + timedelta(days=10),
        )

        notifications = await scan_and_expire(db_session, admin_user.id)

        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_skip_already_expired(self, db_session, admin_user):
        """Already expired timelines should not be re-expired."""
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=5),
            status="expired",
        )

        notifications = await scan_and_expire(db_session, admin_user.id)

        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_multiple_expired(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=1),
        )
        await _make_timeline(
            db_session,
            building.id,
            notification_deadline=date.today() - timedelta(days=10),
            defect_type="pollutant",
        )

        notifications = await scan_and_expire(db_session, admin_user.id)

        assert len(notifications) == 2


# ---------------------------------------------------------------------------
# Fingerprint tests
# ---------------------------------------------------------------------------


class TestFingerprint:
    def test_fingerprint_format(self):
        defect_id = uuid.uuid4()
        fp = _make_fingerprint("defect_deadline_approaching", defect_id)
        assert fp == f"defect:defect_deadline_approaching:{defect_id}"

    def test_fingerprint_uniqueness(self):
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        fp1 = _make_fingerprint("defect_deadline_approaching", id1)
        fp2 = _make_fingerprint("defect_deadline_approaching", id2)
        assert fp1 != fp2
