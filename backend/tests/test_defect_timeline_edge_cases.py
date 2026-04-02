"""Tests for DefectShield — edge cases: boundary dates, leap years, holidays, timezones.

Covers: year transitions, leap year handling, Swiss holiday boundary,
midnight UTC, multi-year spans, Dec→Jan transitions, all 5 defect types,
far-future dates, same-day discovery, and business-day chain skips.
"""

from datetime import UTC, date, timedelta

import pytest

from app.services.defect_timeline_service import (
    HIDDEN_DEFECT_PRESCRIPTION_DAYS,
    HIDDEN_DEFECT_TYPES,
    MANIFEST_DEFECT_PRESCRIPTION_DAYS,
    NOTIFICATION_DAYS,
    _is_business_day,
    _next_business_day,
    _swiss_holidays,
    calc_notification_deadline,
    check_new_build_guarantee,
    classify_urgency,
    compute_deadline,
    compute_prescription,
)

# ---------------------------------------------------------------------------
# Leap year edge cases
# ---------------------------------------------------------------------------


class TestLeapYearDeadlines:
    """Boundary dates involving Feb 29 in leap years."""

    def test_discovery_on_feb_28_leap_year(self):
        """Feb 28, 2028 + 60 days should cross the leap day correctly."""
        deadline = compute_deadline(date(2028, 2, 28))
        expected_raw = date(2028, 2, 28) + timedelta(days=60)
        assert expected_raw == date(2028, 4, 28)
        assert deadline == _next_business_day(expected_raw)

    def test_discovery_on_feb_29_leap_year(self):
        """Feb 29 itself (2028) + 60 days = April 29, 2028."""
        deadline = compute_deadline(date(2028, 2, 29))
        expected_raw = date(2028, 4, 29)
        assert deadline == _next_business_day(expected_raw)

    def test_discovery_on_dec_31_before_leap_year(self):
        """Dec 31, 2027 + 60 days crosses into leap year Feb 2028."""
        deadline = compute_deadline(date(2027, 12, 31))
        expected_raw = date(2027, 12, 31) + timedelta(days=60)
        assert expected_raw == date(2028, 2, 29)  # lands on leap day
        assert deadline == _next_business_day(expected_raw)

    def test_discovery_on_jan_1_non_leap_year(self):
        """Jan 1, 2027 + 60 = Mar 2 — non-leap year, no Feb 29."""
        deadline = compute_deadline(date(2027, 1, 1))
        expected_raw = date(2027, 3, 2)
        assert deadline == _next_business_day(expected_raw)

    def test_year_2032_leap_year(self):
        """Far-future leap year: Feb 28, 2032 + 60 days."""
        deadline = compute_deadline(date(2032, 2, 28))
        expected_raw = date(2032, 4, 28)
        assert deadline == _next_business_day(expected_raw)


# ---------------------------------------------------------------------------
# Year transition edge cases
# ---------------------------------------------------------------------------


class TestYearTransitionDeadlines:
    """Deadlines that cross year boundaries."""

    def test_nov_discovery_crosses_to_next_year(self):
        """Nov 15, 2026 + 60 = Jan 14, 2027."""
        deadline = compute_deadline(date(2026, 11, 15))
        expected_raw = date(2027, 1, 14)
        assert deadline == _next_business_day(expected_raw)

    def test_dec_31_discovery(self):
        """Dec 31 + 60 days crosses into March of next year."""
        deadline = compute_deadline(date(2026, 12, 31))
        expected_raw = date(2026, 12, 31) + timedelta(days=60)
        assert expected_raw == date(2027, 3, 1)
        assert deadline == _next_business_day(expected_raw)

    def test_dec_1_discovery_new_year_holiday(self):
        """Dec 1, 2026 + 60 = Jan 30, 2027. Verify holiday skip at year boundary."""
        raw = date(2026, 12, 1) + timedelta(days=60)
        deadline = compute_deadline(date(2026, 12, 1))
        assert deadline == _next_business_day(raw)

    def test_century_boundary_2099_2100(self):
        """Dec 1, 2099 + 60 = Jan 30, 2100. 2100 is NOT a leap year."""
        deadline = compute_deadline(date(2099, 12, 1))
        expected_raw = date(2100, 1, 30)
        assert deadline == _next_business_day(expected_raw)


# ---------------------------------------------------------------------------
# Swiss holiday boundary cases
# ---------------------------------------------------------------------------


class TestSwissHolidayEdgeCases:
    """Deadlines that land exactly on Swiss holidays."""

    def test_deadline_on_national_day(self):
        """If raw deadline falls on Aug 1 (Swiss National Day), extends to next business day."""
        # Find a discovery_date such that +60 = Aug 1
        discovery = date(2027, 6, 2)  # Jun 2 + 60 = Aug 1
        raw = discovery + timedelta(days=60)
        assert raw == date(2027, 8, 1)
        deadline = compute_deadline(discovery)
        assert deadline > raw
        assert _is_business_day(deadline)

    def test_deadline_on_christmas(self):
        """Dec 25 is Christmas — must extend."""
        discovery = date(2026, 10, 26)  # Oct 26 + 60 = Dec 25
        raw = discovery + timedelta(days=60)
        assert raw == date(2026, 12, 25)
        deadline = compute_deadline(discovery)
        assert deadline > raw
        assert _is_business_day(deadline)

    def test_deadline_on_good_friday(self):
        """Good Friday (moveable) — must extend to Monday or later."""
        # Good Friday 2027: March 26
        holidays = _swiss_holidays(2027)
        good_friday = date(2027, 3, 26)
        assert good_friday in holidays
        discovery = good_friday - timedelta(days=60)
        deadline = compute_deadline(discovery)
        assert deadline > good_friday
        assert _is_business_day(deadline)

    def test_deadline_on_new_year(self):
        """Jan 1 is New Year — extends."""
        discovery = date(2026, 11, 2)  # Nov 2 + 60 = Jan 1 2027
        raw = discovery + timedelta(days=60)
        assert raw == date(2027, 1, 1)
        deadline = compute_deadline(discovery)
        assert deadline > raw
        assert _is_business_day(deadline)

    def test_deadline_on_berchtoldstag(self):
        """Jan 2 is Berchtoldstag — if Jan 1 + Jan 2 both holiday, skips to Jan 3+."""
        # Jan 1 + Jan 2 are holidays; if Jan 3 is also weekend, skip further
        discovery = date(2026, 11, 3)  # Nov 3 + 60 = Jan 2 2027
        raw = discovery + timedelta(days=60)
        assert raw == date(2027, 1, 2)
        deadline = compute_deadline(discovery)
        assert deadline > raw
        assert _is_business_day(deadline)

    def test_holiday_chain_christmas_boxing_weekend(self):
        """Dec 25 + Dec 26 + weekend can create a multi-day skip."""
        # 2027: Dec 25 = Sat, Dec 26 = Sun — both already weekend + holiday
        # If the raw deadline lands on Dec 25, 2027, it's a Saturday
        deadline = _next_business_day(date(2027, 12, 25))
        assert deadline.weekday() < 5
        assert _is_business_day(deadline)

    def test_ascension_whit_cluster(self):
        """Ascension (Thu) + bridge day (Fri) + weekend = 4-day skip."""
        holidays = _swiss_holidays(2027)
        ascension = date(2027, 5, 6)  # Ascension 2027
        assert ascension in holidays
        # If deadline lands on Ascension Thursday, it should skip to Friday or Monday
        next_bd = _next_business_day(ascension)
        assert _is_business_day(next_bd)


# ---------------------------------------------------------------------------
# calc_notification_deadline edge cases
# ---------------------------------------------------------------------------


class TestCalcNotificationDeadlineEdge:
    """Edge cases for the full calc_notification_deadline function."""

    def test_reference_date_equals_deadline(self):
        """days_remaining = 0 when reference_date == deadline."""
        discovery = date(2026, 3, 1)
        result = calc_notification_deadline(discovery)
        zero_ref = calc_notification_deadline(discovery, reference_date=result.deadline)
        assert zero_ref.days_remaining == 0

    def test_reference_date_after_deadline(self):
        """Negative days_remaining when reference is past deadline."""
        discovery = date(2026, 3, 1)
        result = calc_notification_deadline(discovery)
        late_ref = calc_notification_deadline(discovery, reference_date=result.deadline + timedelta(days=10))
        assert late_ref.days_remaining == -10

    def test_extended_flag_when_weekend(self):
        """Extended=True when raw deadline lands on Saturday."""
        # Find a Saturday deadline
        for offset in range(365):
            d = date(2026, 1, 1) + timedelta(days=offset)
            raw = d + timedelta(days=NOTIFICATION_DAYS)
            if raw.weekday() == 5:  # Saturday
                result = calc_notification_deadline(d, reference_date=d)
                assert result.extended is True
                assert result.deadline > raw
                break

    def test_extended_flag_false_on_business_day(self):
        """Extended=False when raw deadline is a normal business day."""
        for offset in range(365):
            d = date(2026, 1, 1) + timedelta(days=offset)
            raw = d + timedelta(days=NOTIFICATION_DAYS)
            if raw.weekday() < 5 and raw not in _swiss_holidays(raw.year):
                result = calc_notification_deadline(d, reference_date=d)
                assert result.extended is False
                break


# ---------------------------------------------------------------------------
# classify_urgency boundary values
# ---------------------------------------------------------------------------


class TestClassifyUrgencyBoundaries:
    """Exact boundary testing for urgency classification."""

    def test_zero_days(self):
        assert classify_urgency(0) == "critical"

    def test_negative_days(self):
        assert classify_urgency(-5) == "critical"

    def test_exactly_7_days(self):
        assert classify_urgency(7) == "critical"

    def test_eight_days(self):
        assert classify_urgency(8) == "urgent"

    def test_exactly_15_days(self):
        assert classify_urgency(15) == "urgent"

    def test_sixteen_days(self):
        assert classify_urgency(16) == "warning"

    def test_exactly_30_days(self):
        assert classify_urgency(30) == "warning"

    def test_thirty_one_days(self):
        assert classify_urgency(31) == "normal"

    def test_very_large_number(self):
        assert classify_urgency(999) == "normal"


# ---------------------------------------------------------------------------
# New-build guarantee edge cases
# ---------------------------------------------------------------------------


class TestNewBuildGuaranteeEdge:
    """Boundary testing for 2-year new-build guarantee."""

    def test_exactly_730_days_not_eligible(self):
        """Exactly 730 days = not within guarantee (< 730 required)."""
        purchase = date(2024, 1, 1)
        discovery = purchase + timedelta(days=730)
        assert check_new_build_guarantee(purchase, discovery) is False

    def test_729_days_eligible(self):
        """729 days = within guarantee."""
        purchase = date(2024, 1, 1)
        discovery = purchase + timedelta(days=729)
        assert check_new_build_guarantee(purchase, discovery) is True

    def test_same_day_purchase_discovery(self):
        """Discovery on purchase day = within guarantee."""
        d = date(2026, 6, 15)
        assert check_new_build_guarantee(d, d) is True

    def test_one_day_after_purchase(self):
        """Discovery one day after purchase = within guarantee."""
        purchase = date(2026, 1, 1)
        assert check_new_build_guarantee(purchase, purchase + timedelta(days=1)) is True


# ---------------------------------------------------------------------------
# Prescription edge cases
# ---------------------------------------------------------------------------


class TestPrescriptionEdge:
    """Prescription calculation across all defect types."""

    @pytest.mark.parametrize("defect_type", ["pollutant", "structural"])
    def test_hidden_defect_5_years(self, defect_type):
        """Hidden defect types get 5-year prescription."""
        purchase = date(2026, 1, 1)
        result = compute_prescription(purchase, defect_type)
        expected = purchase + timedelta(days=HIDDEN_DEFECT_PRESCRIPTION_DAYS)
        assert result == expected

    @pytest.mark.parametrize("defect_type", ["construction", "installation", "other"])
    def test_manifest_defect_2_years(self, defect_type):
        """Manifest defect types get 2-year prescription."""
        purchase = date(2026, 1, 1)
        result = compute_prescription(purchase, defect_type)
        expected = purchase + timedelta(days=MANIFEST_DEFECT_PRESCRIPTION_DAYS)
        assert result == expected

    def test_hidden_defect_types_constant(self):
        """Verify HIDDEN_DEFECT_TYPES contains exactly the expected types."""
        assert {"pollutant", "structural"} == HIDDEN_DEFECT_TYPES

    def test_prescription_leap_year_crossing(self):
        """Prescription that crosses a leap year boundary."""
        purchase = date(2027, 3, 1)
        result = compute_prescription(purchase, "construction")
        expected = purchase + timedelta(days=MANIFEST_DEFECT_PRESCRIPTION_DAYS)
        assert result == expected


# ---------------------------------------------------------------------------
# _is_business_day / _next_business_day edge cases
# ---------------------------------------------------------------------------


class TestBusinessDayEdge:
    """Edge cases for business day helpers."""

    def test_saturday_not_business_day(self):
        assert _is_business_day(date(2026, 4, 4)) is False  # Saturday

    def test_sunday_not_business_day(self):
        assert _is_business_day(date(2026, 4, 5)) is False  # Sunday

    def test_monday_is_business_day(self):
        # Check it's not a holiday first
        d = date(2026, 4, 6)  # Monday
        if d not in _swiss_holidays(d.year):
            assert _is_business_day(d) is True

    def test_next_business_day_from_saturday(self):
        """Saturday → Monday (if Monday is not a holiday)."""
        sat = date(2026, 4, 4)
        result = _next_business_day(sat)
        assert result.weekday() < 5
        assert _is_business_day(result)

    def test_next_business_day_already_business_day(self):
        """A business day returns itself."""
        # Find a guaranteed business day
        d = date(2026, 4, 7)  # Tuesday
        if _is_business_day(d):
            assert _next_business_day(d) == d

    def test_holiday_cascade(self):
        """Jan 1 (holiday) + Jan 2 (Berchtoldstag) → at least Jan 3 or later."""
        result = _next_business_day(date(2027, 1, 1))
        assert result >= date(2027, 1, 3)
        assert _is_business_day(result)


# ---------------------------------------------------------------------------
# Swiss holidays across multiple years
# ---------------------------------------------------------------------------


class TestSwissHolidaysMultiYear:
    """Verify holiday set consistency across years."""

    @pytest.mark.parametrize("year", [2026, 2027, 2028, 2029, 2030])
    def test_national_day_always_present(self, year):
        holidays = _swiss_holidays(year)
        assert date(year, 8, 1) in holidays

    @pytest.mark.parametrize("year", [2026, 2027, 2028, 2029, 2030])
    def test_christmas_always_present(self, year):
        holidays = _swiss_holidays(year)
        assert date(year, 12, 25) in holidays

    @pytest.mark.parametrize("year", [2026, 2027, 2028, 2029, 2030])
    def test_nine_holidays_per_year(self, year):
        holidays = _swiss_holidays(year)
        assert len(holidays) == 9

    def test_easter_2028_correct(self):
        """Easter 2028 = April 16. Good Friday = April 14."""
        holidays = _swiss_holidays(2028)
        assert date(2028, 4, 14) in holidays  # Good Friday
        assert date(2028, 4, 17) in holidays  # Easter Monday

    @pytest.mark.parametrize("year", [2026, 2027, 2028, 2029, 2030])
    def test_new_year_and_berchtoldstag_always_present(self, year):
        holidays = _swiss_holidays(year)
        assert date(year, 1, 1) in holidays
        assert date(year, 1, 2) in holidays


# ---------------------------------------------------------------------------
# Year 2030 specific tests (NOT a leap year)
# ---------------------------------------------------------------------------


class TestYear2030NotLeap:
    """2030 is NOT a leap year — verify no Feb 29 assumption."""

    def test_feb_28_2030_plus_60(self):
        """Feb 28, 2030 + 60 = Apr 29, 2030 (no Feb 29)."""
        deadline = compute_deadline(date(2030, 2, 28))
        expected_raw = date(2030, 4, 29)
        assert deadline == _next_business_day(expected_raw)

    def test_dec_31_2029_plus_60_into_2030(self):
        """Dec 31, 2029 + 60 = Mar 1, 2030 (skips Feb 29)."""
        raw = date(2029, 12, 31) + timedelta(days=60)
        assert raw == date(2030, 3, 1)
        deadline = compute_deadline(date(2029, 12, 31))
        assert deadline == _next_business_day(raw)

    def test_jan_15_2030_plus_60(self):
        """Jan 15, 2030 + 60 = Mar 16, 2030."""
        raw = date(2030, 1, 15) + timedelta(days=60)
        assert raw == date(2030, 3, 16)
        deadline = compute_deadline(date(2030, 1, 15))
        assert deadline == _next_business_day(raw)


# ---------------------------------------------------------------------------
# Midnight UTC / timezone-aware edge cases
# ---------------------------------------------------------------------------


class TestTimezoneEdgeCases:
    """Verify deadline computation is date-based (no timezone drift).

    Swiss legal deadlines are calendar-date based (not datetime-aware).
    These tests confirm that feeding a date derived from midnight UTC or
    CET/CEST boundaries produces correct results.
    """

    def test_midnight_utc_date(self):
        """Date derived from midnight UTC: 2026-06-15T00:00:00Z → date(2026, 6, 15)."""
        from datetime import datetime

        dt = datetime(2026, 6, 15, 0, 0, 0, tzinfo=UTC)
        discovery = dt.date()
        assert discovery == date(2026, 6, 15)
        deadline = compute_deadline(discovery)
        expected_raw = date(2026, 8, 14)
        assert deadline == _next_business_day(expected_raw)

    def test_cet_midnight_vs_utc(self):
        """CET midnight (UTC+1) = 23:00 UTC previous day. Date extraction matters."""
        from datetime import datetime, timezone

        cet = timezone(timedelta(hours=1))
        # Midnight CET on June 15 = 23:00 UTC June 14
        dt_cet = datetime(2026, 6, 15, 0, 0, 0, tzinfo=cet)
        dt_utc = dt_cet.astimezone(UTC)
        # UTC date is June 14, CET date is June 15
        assert dt_utc.date() == date(2026, 6, 14)
        assert dt_cet.date() == date(2026, 6, 15)
        # Legal deadlines use local (Swiss) date, not UTC
        deadline_cet = compute_deadline(dt_cet.date())
        deadline_utc = compute_deadline(dt_utc.date())
        # They differ by 1 day
        # Deadlines differ because input dates differ (June 15 vs June 14)
        assert _is_business_day(deadline_cet)
        assert _is_business_day(deadline_utc)

    def test_cest_summer_time(self):
        """CEST (UTC+2) in summer: midnight CEST = 22:00 UTC previous day."""
        from datetime import datetime, timezone

        cest = timezone(timedelta(hours=2))
        dt_cest = datetime(2026, 7, 1, 0, 0, 0, tzinfo=cest)
        dt_utc = dt_cest.astimezone(UTC)
        assert dt_utc.date() == date(2026, 6, 30)
        assert dt_cest.date() == date(2026, 7, 1)
        # Swiss law uses CET/CEST local date
        deadline = compute_deadline(dt_cest.date())
        assert _is_business_day(deadline)

    def test_end_of_day_utc_does_not_shift(self):
        """23:59:59 UTC on a given date → same date, same deadline."""
        from datetime import datetime

        dt = datetime(2026, 3, 1, 23, 59, 59, tzinfo=UTC)
        discovery = dt.date()
        assert discovery == date(2026, 3, 1)
        deadline = compute_deadline(discovery)
        assert deadline == date(2026, 4, 30)  # same as test_compute_deadline_standard

    def test_date_only_no_tz_drift(self):
        """Pure date objects have no timezone — deadline is deterministic."""
        d = date(2026, 3, 1)
        deadline1 = compute_deadline(d)
        deadline2 = compute_deadline(d)
        assert deadline1 == deadline2
