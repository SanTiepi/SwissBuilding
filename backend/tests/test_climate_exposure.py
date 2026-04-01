"""Tests for climate exposure and opportunity window engine."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.climate_opportunity_service import (
    WORK_TYPE_SEASONS,
    _derive_stress,
    _estimate_freeze_thaw,
    _estimate_hdd,
    _estimate_precipitation,
    _occupancy_windows,
    _safe_float,
    _seasonal_windows,
    _weather_windows,
    _wind_from_altitude,
)

# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------


class TestSafeFloat:
    def test_none(self):
        assert _safe_float(None) is None

    def test_int(self):
        assert _safe_float(42) == 42.0

    def test_float(self):
        assert _safe_float(3.14) == 3.14

    def test_str(self):
        assert _safe_float("55.3") == 55.3

    def test_str_with_unit(self):
        assert _safe_float("45.2 dB") == 45.2

    def test_bad_str(self):
        assert _safe_float("abc") is None


class TestEstimateHDD:
    def test_none(self):
        assert _estimate_hdd(None) is None

    def test_low_altitude(self):
        hdd = _estimate_hdd(400)
        assert hdd == 3400.0

    def test_high_altitude(self):
        hdd = _estimate_hdd(1400)
        assert hdd is not None
        assert hdd > 3400

    def test_above_reference(self):
        # 1000m above reference (400m) => +1000 HDD
        hdd = _estimate_hdd(1400)
        assert hdd == 3400 + 1000


class TestEstimatePrecipitation:
    def test_none(self):
        assert _estimate_precipitation(None) is None

    def test_plateau(self):
        precip = _estimate_precipitation(400)
        assert precip == 1000

    def test_mountain(self):
        precip = _estimate_precipitation(1400)
        assert precip is not None
        assert precip > 1000


class TestEstimateFreezeThaw:
    def test_none(self):
        assert _estimate_freeze_thaw(None) is None

    def test_low(self):
        assert _estimate_freeze_thaw(300) == 40

    def test_mid(self):
        assert _estimate_freeze_thaw(800) == 60

    def test_high(self):
        assert _estimate_freeze_thaw(1200) == 90

    def test_very_high(self):
        assert _estimate_freeze_thaw(2000) == 120


class TestWindFromAltitude:
    def test_none(self):
        assert _wind_from_altitude(None) is None

    def test_low(self):
        assert _wind_from_altitude(400) == "sheltered"

    def test_mid(self):
        assert _wind_from_altitude(1200) == "moderate"

    def test_high(self):
        assert _wind_from_altitude(1800) == "exposed"


class TestDeriveStress:
    def test_all_unknown(self):
        result = _derive_stress(None, None, None)
        assert result["moisture"] == "unknown"
        assert result["thermal"] == "unknown"
        assert result["uv"] == "unknown"

    def test_high_precipitation(self):
        result = _derive_stress(None, 1600, None)
        assert result["moisture"] == "high"

    def test_moderate_precipitation(self):
        result = _derive_stress(None, 1200, None)
        assert result["moisture"] == "moderate"

    def test_low_precipitation(self):
        result = _derive_stress(None, 800, None)
        assert result["moisture"] == "low"

    def test_high_thermal(self):
        result = _derive_stress(None, None, 5000)
        assert result["thermal"] == "high"

    def test_moderate_thermal(self):
        result = _derive_stress(None, None, 4000)
        assert result["thermal"] == "moderate"

    def test_low_thermal(self):
        result = _derive_stress(None, None, 3000)
        assert result["thermal"] == "low"

    def test_high_uv(self):
        result = _derive_stress(2000, None, None)
        assert result["uv"] == "high"

    def test_moderate_uv(self):
        result = _derive_stress(1200, None, None)
        assert result["uv"] == "moderate"

    def test_low_uv(self):
        result = _derive_stress(400, None, None)
        assert result["uv"] == "low"


# ---------------------------------------------------------------------------
# Window detection — pure functions
# ---------------------------------------------------------------------------


class TestWeatherWindows:
    def test_detects_dry_season(self):
        today = date(2026, 3, 1)
        horizon = today + timedelta(days=365)

        class FakeBuilding:
            pass

        windows = _weather_windows(today, horizon, FakeBuilding())
        assert len(windows) >= 1
        assert windows[0]["window_type"] == "weather"
        assert "seche" in windows[0]["title"].lower()

    def test_no_windows_if_past(self):
        """If horizon is before next dry season, no windows."""
        today = date(2026, 11, 1)
        horizon = today + timedelta(days=30)  # Only November

        class FakeBuilding:
            pass

        windows = _weather_windows(today, horizon, FakeBuilding())
        # Should detect nothing (Nov 1 to Dec 1 — outside dry season of current year,
        # next year dry season starts Apr which is beyond horizon)
        assert len(windows) == 0


class TestSeasonalWindows:
    def test_detects_summer_hvac(self):
        today = date(2026, 3, 1)
        horizon = today + timedelta(days=365)
        windows = _seasonal_windows(today, horizon)
        assert len(windows) >= 1
        hvac = [w for w in windows if "chauffage" in w["title"].lower()]
        assert len(hvac) >= 1


class TestOccupancyWindows:
    def test_detects_vacation_periods(self):
        today = date(2026, 3, 1)
        horizon = today + timedelta(days=365)
        windows = _occupancy_windows(today, horizon)
        assert len(windows) >= 1
        summer = [w for w in windows if "ete" in w["title"].lower()]
        assert len(summer) >= 1


# ---------------------------------------------------------------------------
# Work type seasons coverage
# ---------------------------------------------------------------------------


class TestWorkTypeSeasons:
    def test_all_have_required_keys(self):
        for wt, info in WORK_TYPE_SEASONS.items():
            assert "label" in info, f"{wt} missing label"
            assert "best_months" in info, f"{wt} missing best_months"
            assert "reason" in info, f"{wt} missing reason"
            assert len(info["best_months"]) > 0, f"{wt} has empty best_months"

    def test_months_valid(self):
        for wt, info in WORK_TYPE_SEASONS.items():
            for m in info["best_months"]:
                assert 1 <= m <= 12, f"{wt} has invalid month {m}"

    def test_key_work_types_present(self):
        """Ensure pollutant-related work types are covered."""
        for key in ("desamiantage", "radon", "pcb", "plomb"):
            assert key in WORK_TYPE_SEASONS, f"Missing work type: {key}"
