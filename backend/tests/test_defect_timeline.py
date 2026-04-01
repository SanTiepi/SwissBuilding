"""Tests for DefectShield — construction defect deadline calculator.

Art. 367 al. 1bis CO: 60 calendar days from discovery (since 01.01.2026).
Includes: weekend/holiday skip logic, transition validation.
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.schemas.defect_timeline import DefectTimelineCreate
from app.services.defect_timeline_service import (
    HIDDEN_DEFECT_PRESCRIPTION_DAYS,
    MANIFEST_DEFECT_PRESCRIPTION_DAYS,
    NEW_BUILD_GUARANTEE_DAYS,
    _is_business_day,
    _next_business_day,
    _swiss_holidays,
    calc_notification_deadline,
    check_new_build_guarantee,
    classify_urgency,
    compute_deadline,
    compute_prescription,
    create_timeline,
    detect_expired,
    get_active_alerts,
    get_timeline,
    list_building_timelines,
    update_defect_status,
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
        """Art. 367 al. 1bis CO: 60 days from discovery, weekday landing."""
        discovery = date(2026, 3, 1)
        deadline = compute_deadline(discovery)
        # 2026-04-30 is Thursday — no extension needed
        assert deadline == date(2026, 4, 30)

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
        # 2028-03-15 is Wednesday — no extension
        assert deadline == date(2028, 3, 15)

    def test_compute_deadline_year_boundary(self):
        """Deadline crosses year boundary."""
        discovery = date(2026, 12, 15)
        deadline = compute_deadline(discovery)
        # 2027-02-13 is Saturday → extends to Monday 2027-02-15
        assert deadline == date(2027, 2, 15)  # Monday

    def test_compute_deadline_lands_on_saturday(self):
        """60th day on Saturday → extends to Monday."""
        # 2026-06-01 + 60 = 2026-07-31 (Friday) — no extension
        # 2026-06-02 + 60 = 2026-08-01 (Saturday) → Monday 2026-08-03
        discovery = date(2026, 6, 2)
        deadline = compute_deadline(discovery)
        assert deadline == date(2026, 8, 3)  # Monday
        assert deadline.weekday() == 0

    def test_compute_deadline_lands_on_sunday(self):
        """60th day on Sunday → extends to Monday."""
        # 2026-06-03 + 60 = 2026-08-02 (Sunday) → Monday 2026-08-03
        discovery = date(2026, 6, 3)
        deadline = compute_deadline(discovery)
        assert deadline == date(2026, 8, 3)  # Monday
        assert deadline.weekday() == 0

    def test_compute_deadline_lands_on_christmas(self):
        """60th day on Dec 25 (Christmas) → extends to next business day."""
        # 2026-10-26 + 60 = 2026-12-25 (Friday, Christmas)
        discovery = date(2026, 10, 26)
        deadline = compute_deadline(discovery)
        # Dec 25 (Fri, Christmas) → Dec 26 (Sat, St Stephen) → Dec 28 (Mon)
        assert deadline == date(2026, 12, 28)

    def test_compute_deadline_lands_on_national_day(self):
        """60th day on Aug 1 (Swiss National Day) → extends."""
        # 2026-06-02 + 60 = 2026-08-01 (Saturday + National Day)
        discovery = date(2026, 6, 2)
        deadline = compute_deadline(discovery)
        assert deadline == date(2026, 8, 3)  # Monday

    def test_compute_deadline_lands_on_new_year(self):
        """60th day on Jan 1 → extends past Jan 2 (Berchtoldstag) to Jan 3 or later."""
        # 2026-11-02 + 60 = 2027-01-01 (Friday, New Year)
        discovery = date(2026, 11, 2)
        deadline = compute_deadline(discovery)
        # Jan 1 (Fri, New Year) → Jan 2 (Sat, also Berchtoldstag) → Jan 4 (Mon)
        assert deadline == date(2027, 1, 4)


# ---------------------------------------------------------------------------
# Swiss holidays tests
# ---------------------------------------------------------------------------


class TestSwissHolidays:
    def test_known_2026_holidays(self):
        holidays = _swiss_holidays(2026)
        assert date(2026, 1, 1) in holidays  # New Year
        assert date(2026, 1, 2) in holidays  # Berchtoldstag
        assert date(2026, 8, 1) in holidays  # National Day
        assert date(2026, 12, 25) in holidays  # Christmas
        assert date(2026, 12, 26) in holidays  # St Stephen

    def test_easter_2026(self):
        """Easter 2026 is April 5."""
        holidays = _swiss_holidays(2026)
        assert date(2026, 4, 3) in holidays  # Good Friday
        assert date(2026, 4, 6) in holidays  # Easter Monday

    def test_easter_2027(self):
        """Easter 2027 is March 28."""
        holidays = _swiss_holidays(2027)
        assert date(2027, 3, 26) in holidays  # Good Friday
        assert date(2027, 3, 29) in holidays  # Easter Monday

    def test_ascension_whit_monday_2026(self):
        holidays = _swiss_holidays(2026)
        # Easter 2026 = April 5
        assert date(2026, 5, 14) in holidays  # Ascension (Easter + 39)
        assert date(2026, 5, 25) in holidays  # Whit Monday (Easter + 50)

    def test_is_business_day_weekday(self):
        assert _is_business_day(date(2026, 4, 1)) is True  # Wednesday

    def test_is_business_day_saturday(self):
        assert _is_business_day(date(2026, 4, 4)) is False  # Saturday

    def test_is_business_day_sunday(self):
        assert _is_business_day(date(2026, 4, 5)) is False  # Sunday (Easter)

    def test_is_business_day_holiday(self):
        assert _is_business_day(date(2026, 12, 25)) is False  # Christmas

    def test_next_business_day_already_business_day(self):
        assert _next_business_day(date(2026, 4, 1)) == date(2026, 4, 1)

    def test_next_business_day_weekend(self):
        assert _next_business_day(date(2026, 4, 4)) == date(2026, 4, 7)  # Sat → Mon

    def test_next_business_day_holiday_chain(self):
        """Christmas (Fri) + St Stephen (Sat) + Sun → Monday."""
        assert _next_business_day(date(2026, 12, 25)) == date(2026, 12, 28)


# ---------------------------------------------------------------------------
# calc_notification_deadline tests
# ---------------------------------------------------------------------------


class TestCalcNotificationDeadline:
    def test_basic_result_structure(self):
        result = calc_notification_deadline(date(2026, 3, 1), reference_date=date(2026, 3, 1))
        assert hasattr(result, "deadline")
        assert hasattr(result, "days_remaining")
        assert hasattr(result, "extended")

    def test_no_extension_needed(self):
        """Deadline on a normal weekday: extended=False."""
        # 2026-03-01 + 60 = 2026-04-30 (Thursday)
        result = calc_notification_deadline(date(2026, 3, 1), reference_date=date(2026, 3, 1))
        assert result.deadline == date(2026, 4, 30)
        assert result.days_remaining == 60
        assert result.extended is False

    def test_extension_on_weekend(self):
        """Deadline on Saturday → extends, extended=True."""
        # 2026-06-02 + 60 = 2026-08-01 (Sat) → 2026-08-03 (Mon)
        result = calc_notification_deadline(date(2026, 6, 2), reference_date=date(2026, 6, 2))
        assert result.deadline == date(2026, 8, 3)
        assert result.days_remaining == 62
        assert result.extended is True

    def test_extension_on_holiday(self):
        """Deadline on Christmas → extends, extended=True."""
        # 2026-10-26 + 60 = 2026-12-25 (Fri, Christmas) → Mon Dec 28
        result = calc_notification_deadline(date(2026, 10, 26), reference_date=date(2026, 10, 26))
        assert result.deadline == date(2026, 12, 28)
        assert result.extended is True

    def test_days_remaining_negative_when_past(self):
        """If reference_date is after deadline, days_remaining is negative."""
        result = calc_notification_deadline(date(2026, 1, 1), reference_date=date(2026, 6, 1))
        assert result.days_remaining < 0

    def test_days_remaining_zero_on_deadline_day(self):
        """If reference_date equals deadline, days_remaining=0."""
        result = calc_notification_deadline(date(2026, 3, 1), reference_date=date(2026, 4, 30))
        assert result.days_remaining == 0

    def test_defaults_to_today(self):
        """Without reference_date, uses today."""
        result = calc_notification_deadline(date.today())
        assert result.days_remaining == (result.deadline - date.today()).days

    def test_good_friday_extension(self):
        """Deadline landing on Good Friday 2026 (April 3) → extends past Easter Monday."""
        # 2026-02-02 + 60 = 2026-04-03 (Good Friday)
        result = calc_notification_deadline(date(2026, 2, 2), reference_date=date(2026, 2, 2))
        # Good Friday (Fri) → Sat → Sun → Easter Monday (holiday) → Tue April 7
        assert result.deadline == date(2026, 4, 7)
        assert result.extended is True


# ---------------------------------------------------------------------------
# update_defect_status tests
# ---------------------------------------------------------------------------


class TestUpdateDefectStatus:
    async def test_active_to_notified(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        updated = await update_defect_status(db_session, timeline.id, "notified")
        assert updated.status == "notified"

    async def test_active_to_expired(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        updated = await update_defect_status(db_session, timeline.id, "expired")
        assert updated.status == "expired"

    async def test_active_to_resolved(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        updated = await update_defect_status(db_session, timeline.id, "resolved")
        assert updated.status == "resolved"

    async def test_notified_to_resolved(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        await update_defect_status(db_session, timeline.id, "notified")
        updated = await update_defect_status(db_session, timeline.id, "resolved")
        assert updated.status == "resolved"

    async def test_expired_to_resolved(self, db_session, admin_user):
        """Late notification is still allowed."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        await update_defect_status(db_session, timeline.id, "expired")
        updated = await update_defect_status(db_session, timeline.id, "resolved")
        assert updated.status == "resolved"

    async def test_resolved_is_terminal(self, db_session, admin_user):
        """Cannot transition out of resolved."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        await update_defect_status(db_session, timeline.id, "resolved")
        with pytest.raises(ValueError, match="terminal state"):
            await update_defect_status(db_session, timeline.id, "active")

    async def test_invalid_transition_notified_to_active(self, db_session, admin_user):
        """Cannot go back from notified to active."""
        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        await update_defect_status(db_session, timeline.id, "notified")
        with pytest.raises(ValueError, match="Invalid transition"):
            await update_defect_status(db_session, timeline.id, "active")

    async def test_not_found_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await update_defect_status(db_session, uuid.uuid4(), "notified")

    async def test_kwargs_forwarded(self, db_session, admin_user):
        """Extra kwargs (e.g. notified_at) are set on the model."""
        from datetime import datetime

        building = await _make_building(db_session, admin_user.id)
        timeline = await create_timeline(
            db_session,
            DefectTimelineCreate(
                building_id=building.id,
                defect_type="construction",
                discovery_date=date(2026, 3, 1),
            ),
        )
        now = datetime(2026, 4, 15, 10, 0, 0)
        updated = await update_defect_status(
            db_session, timeline.id, "notified", notified_at=now
        )
        assert updated.notified_at == now


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
        # days_remaining >= 60 because deadline may extend past weekends/holidays
        assert alerts[0].days_remaining >= 60

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
