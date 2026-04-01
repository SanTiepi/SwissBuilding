"""Tests for DefectShield — construction defect deadline calculator.

Art. 367 al. 1bis CO: 60 calendar days from discovery (since 01.01.2026).
"""

import uuid
from datetime import date, timedelta

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.schemas.defect_timeline import DefectTimelineCreate
from app.services.defect_timeline_service import (
    HIDDEN_DEFECT_PRESCRIPTION_DAYS,
    MANIFEST_DEFECT_PRESCRIPTION_DAYS,
    NEW_BUILD_GUARANTEE_DAYS,
    NOTIFICATION_DAYS,
    check_new_build_guarantee,
    classify_urgency,
    compute_deadline,
    compute_prescription,
    create_timeline,
    detect_expired,
    get_active_alerts,
    get_timeline,
    list_building_timelines,
    update_timeline_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Defect 1",
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


async def _make_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "diagnostic_context": "AvT",
        "status": "completed",
        "date_inspection": date(2026, 1, 15),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


# ---------------------------------------------------------------------------
# Pure computation tests
# ---------------------------------------------------------------------------


class TestComputeDeadline:
    def test_compute_deadline_standard(self):
        """Art. 367 al. 1bis CO: 60 days from discovery."""
        discovery = date(2026, 3, 1)
        deadline = compute_deadline(discovery)
        assert deadline == date(2026, 4, 30)
        assert (deadline - discovery).days == NOTIFICATION_DAYS

    def test_compute_deadline_edge_day59(self):
        """Day 59 is still before the deadline."""
        discovery = date(2026, 1, 1)
        deadline = compute_deadline(discovery)
        day_59 = discovery + timedelta(days=59)
        assert day_59 < deadline

    def test_compute_deadline_leap_year(self):
        """Deadline calculation works across Feb 29."""
        discovery = date(2028, 1, 15)  # 2028 is a leap year
        deadline = compute_deadline(discovery)
        assert deadline == date(2028, 3, 15)

    def test_compute_deadline_year_boundary(self):
        """Deadline crosses year boundary."""
        discovery = date(2026, 12, 15)
        deadline = compute_deadline(discovery)
        assert deadline == date(2027, 2, 13)


class TestNewBuildGuarantee:
    def test_new_build_guarantee_within_2_years(self):
        """Purchase 1 year ago: guarantee active."""
        purchase = date(2025, 3, 1)
        discovery = date(2026, 2, 28)
        assert check_new_build_guarantee(purchase, discovery) is True

    def test_new_build_guarantee_over_2_years(self):
        """Purchase 3 years ago: guarantee expired."""
        purchase = date(2023, 1, 1)
        discovery = date(2026, 3, 1)
        assert check_new_build_guarantee(purchase, discovery) is False

    def test_new_build_guarantee_exact_2_years(self):
        """Exactly 730 days: guarantee expired (< 730, not <=)."""
        purchase = date(2024, 3, 1)
        discovery = purchase + timedelta(days=NEW_BUILD_GUARANTEE_DAYS)
        assert check_new_build_guarantee(purchase, discovery) is False

    def test_new_build_guarantee_day_before_expiry(self):
        """729 days: guarantee still active."""
        purchase = date(2024, 3, 1)
        discovery = purchase + timedelta(days=NEW_BUILD_GUARANTEE_DAYS - 1)
        assert check_new_build_guarantee(purchase, discovery) is True


class TestComputePrescription:
    def test_prescription_hidden_defect_5_years(self):
        """Hidden defects (pollutant, structural): 5-year prescription."""
        purchase = date(2022, 1, 1)
        result = compute_prescription(purchase, "pollutant")
        assert result == purchase + timedelta(days=HIDDEN_DEFECT_PRESCRIPTION_DAYS)

    def test_prescription_structural_5_years(self):
        """Structural defects also get 5-year prescription."""
        purchase = date(2022, 6, 15)
        result = compute_prescription(purchase, "structural")
        assert result == purchase + timedelta(days=HIDDEN_DEFECT_PRESCRIPTION_DAYS)

    def test_prescription_manifest_defect_2_years(self):
        """Manifest defects (construction, installation, other): 2-year prescription."""
        purchase = date(2024, 1, 1)
        result = compute_prescription(purchase, "construction")
        assert result == purchase + timedelta(days=MANIFEST_DEFECT_PRESCRIPTION_DAYS)

    def test_prescription_installation_2_years(self):
        """Installation defect is manifest: 2 years."""
        purchase = date(2024, 1, 1)
        result = compute_prescription(purchase, "installation")
        assert result == purchase + timedelta(days=MANIFEST_DEFECT_PRESCRIPTION_DAYS)

    def test_prescription_other_2_years(self):
        """'other' defect type: 2 years."""
        purchase = date(2024, 1, 1)
        result = compute_prescription(purchase, "other")
        assert result == purchase + timedelta(days=MANIFEST_DEFECT_PRESCRIPTION_DAYS)


class TestClassifyUrgency:
    def test_critical(self):
        assert classify_urgency(5) == "critical"
        assert classify_urgency(7) == "critical"

    def test_urgent(self):
        assert classify_urgency(10) == "urgent"
        assert classify_urgency(15) == "urgent"

    def test_warning(self):
        assert classify_urgency(20) == "warning"
        assert classify_urgency(30) == "warning"

    def test_normal(self):
        assert classify_urgency(31) == "normal"
        assert classify_urgency(60) == "normal"


# ---------------------------------------------------------------------------
# Service-level DB tests
# ---------------------------------------------------------------------------


class TestCreateTimeline:
    async def test_create_timeline_basic(self, db_session, admin_user):
        """Create a simple defect timeline without purchase date."""
        building = await _make_building(db_session, admin_user.id)
        data = DefectTimelineCreate(
            building_id=building.id,
            defect_type="construction",
            description="Fissure in concrete wall",
            discovery_date=date(2026, 3, 1),
        )
        timeline = await create_timeline(db_session, data)

        assert timeline.id is not None
        assert timeline.building_id == building.id
        assert timeline.defect_type == "construction"
        assert timeline.notification_deadline == date(2026, 4, 30)
        assert timeline.guarantee_type == "standard"
        assert timeline.prescription_date is None
        assert timeline.status == "active"

    async def test_create_timeline_with_diagnostic_link(self, db_session, admin_user):
        """Create timeline linked to a diagnostic."""
        building = await _make_building(db_session, admin_user.id)
        diagnostic = await _make_diagnostic(db_session, building.id)
        data = DefectTimelineCreate(
            building_id=building.id,
            diagnostic_id=diagnostic.id,
            defect_type="pollutant",
            description="Asbestos found in floor tiles",
            discovery_date=date(2026, 2, 15),
            purchase_date=date(2025, 6, 1),
        )
        timeline = await create_timeline(db_session, data)

        assert timeline.diagnostic_id == diagnostic.id
        assert timeline.guarantee_type == "new_build_rectification"
        assert timeline.prescription_date is not None

    async def test_create_timeline_old_purchase_standard_guarantee(self, db_session, admin_user):
        """Purchase >2 years ago: standard guarantee, not new_build_rectification."""
        building = await _make_building(db_session, admin_user.id)
        data = DefectTimelineCreate(
            building_id=building.id,
            defect_type="installation",
            discovery_date=date(2026, 3, 1),
            purchase_date=date(2020, 1, 1),
        )
        timeline = await create_timeline(db_session, data)

        assert timeline.guarantee_type == "standard"
        assert timeline.prescription_date is not None


class TestListBuildingTimelines:
    async def test_list_building_timelines(self, db_session, admin_user):
        """List timelines for a specific building."""
        building = await _make_building(db_session, admin_user.id)
        for i in range(3):
            await create_timeline(
                db_session,
                DefectTimelineCreate(
                    building_id=building.id,
                    defect_type="construction",
                    discovery_date=date(2026, 3, 1) + timedelta(days=i * 10),
                ),
            )
        timelines = await list_building_timelines(db_session, building.id)
        assert len(timelines) == 3

    async def test_multiple_defects_same_building(self, db_session, admin_user):
        """Multiple defect types on the same building."""
        building = await _make_building(db_session, admin_user.id)
        types = ["construction", "pollutant", "structural", "installation", "other"]
        for dt in types:
            await create_timeline(
                db_session,
                DefectTimelineCreate(
                    building_id=building.id,
                    defect_type=dt,
                    discovery_date=date(2026, 3, 15),
                    purchase_date=date(2024, 1, 1),
                ),
            )
        timelines = await list_building_timelines(db_session, building.id)
        assert len(timelines) == 5
        result_types = {t.defect_type for t in timelines}
        assert result_types == set(types)

    async def test_list_empty_building(self, db_session, admin_user):
        """No timelines returns empty list."""
        building = await _make_building(db_session, admin_user.id)
        timelines = await list_building_timelines(db_session, building.id)
        assert timelines == []


class TestAlerts:
    async def test_alerts_within_threshold(self, db_session, admin_user):
        """Alerts return defects within the threshold window."""
        building = await _make_building(db_session, admin_user.id)
        today = date.today()
        # Create a defect discovered today -> deadline in 60 days
        await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=today,
            ),
        )
        # Default threshold is 45 days — deadline at 60 days should NOT appear
        alerts = await get_active_alerts(db_session, days_threshold=45)
        assert len(alerts) == 0

        # With threshold 65 days — should appear
        alerts = await get_active_alerts(db_session, days_threshold=65)
        assert len(alerts) == 1
        assert alerts[0].days_remaining == 60

    async def test_alerts_no_active(self, db_session, admin_user):
        """No active defects: empty alerts."""
        building = await _make_building(db_session, admin_user.id)
        # Create and immediately resolve
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date.today(),
            ),
        )
        await update_timeline_status(db_session, timeline.id, "resolved")

        alerts = await get_active_alerts(db_session, days_threshold=365)
        assert len(alerts) == 0

    async def test_alerts_urgency_levels(self, db_session, admin_user):
        """Different urgency levels based on days remaining."""
        building = await _make_building(db_session, admin_user.id)
        today = date.today()

        # Create defects with varying discovery dates to get different days_remaining
        # 5 days remaining -> critical
        await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                description="critical defect",
                discovery_date=today - timedelta(days=55),
            ),
        )
        # 12 days remaining -> urgent
        await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="pollutant",
                description="urgent defect",
                discovery_date=today - timedelta(days=48),
            ),
        )

        alerts = await get_active_alerts(db_session, days_threshold=60)
        assert len(alerts) == 2
        urgencies = {a.description: a.urgency for a in alerts}
        assert urgencies["critical defect"] == "critical"
        assert urgencies["urgent defect"] == "urgent"


class TestStatusTransitions:
    async def test_status_transitions(self, db_session, admin_user):
        """active -> notified -> resolved transitions."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        assert timeline.status == "active"

        # active -> notified
        updated = await update_timeline_status(db_session, timeline.id, "notified")
        assert updated is not None
        assert updated.status == "notified"

        # notified -> resolved
        updated = await update_timeline_status(db_session, timeline.id, "resolved")
        assert updated is not None
        assert updated.status == "resolved"

    async def test_update_nonexistent_returns_none(self, db_session):
        """Update on nonexistent ID returns None."""
        result = await update_timeline_status(db_session, uuid.uuid4(), "notified")
        assert result is None


class TestExpiredDetection:
    async def test_expired_defect_detection(self, db_session, admin_user):
        """Defects past their deadline are marked expired."""
        building = await _make_building(db_session, admin_user.id)
        today = date.today()

        # Create a defect that was discovered 90 days ago -> deadline was 30 days ago
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=today - timedelta(days=90),
            ),
        )
        assert timeline.status == "active"

        expired = await detect_expired(db_session)
        assert len(expired) == 1
        assert expired[0].id == timeline.id
        assert expired[0].status == "expired"

    async def test_detect_expired_skips_notified(self, db_session, admin_user):
        """Already-notified defects are not marked expired."""
        building = await _make_building(db_session, admin_user.id)
        today = date.today()

        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=today - timedelta(days=90),
            ),
        )
        await update_timeline_status(db_session, timeline.id, "notified")

        expired = await detect_expired(db_session)
        assert len(expired) == 0


class TestGetTimeline:
    async def test_get_timeline(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        fetched = await get_timeline(db_session, timeline.id)
        assert fetched is not None
        assert fetched.id == timeline.id

    async def test_get_timeline_not_found(self, db_session):
        fetched = await get_timeline(db_session, uuid.uuid4())
        assert fetched is None
