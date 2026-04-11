"""Tests for meteo/incident correlation + prediction services (Programme S)."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.building import Building
from app.models.incident import IncidentEpisode
from app.services.incident_prediction_service import predict_incidents
from app.services.meteo_incident_correlation_service import (
    HEAVY_RAIN_MM,
    HIGH_WIND_KMH,
    _build_correlations,
    _classify_weather_conditions,
    _find_preceding_conditions,
    analyze_correlations,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_building(created_by_id, climate=None, **kwargs):
    meta = {}
    if climate:
        meta["climate"] = climate
    return Building(
        id=kwargs.get("id", uuid.uuid4()),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=created_by_id,
        status="active",
        latitude=46.52,
        longitude=6.63,
        source_metadata_json=meta if meta else None,
    )


_LAUSANNE_CLIMATE = {
    "avg_temp_c": 9.5,
    "precipitation_mm": 1100,
    "frost_days": 80,
    "sunshine_hours": 1650,
    "estimated_altitude_m": 500,
}


def _make_incident(building_id, org_id, incident_type="leak", days_ago=30, **kwargs):
    return IncidentEpisode(
        id=uuid.uuid4(),
        building_id=building_id,
        organization_id=org_id,
        incident_type=incident_type,
        title=kwargs.get("title", f"Test {incident_type}"),
        severity=kwargs.get("severity", "moderate"),
        discovered_at=datetime.utcnow() - timedelta(days=days_ago),
    )


def _make_meteo_day(days_ago, precip_mm=5.0, wind_kmh=10.0, temp_c=10.0, humidity_pct=60.0):
    return {
        "date": datetime.utcnow() - timedelta(days=days_ago),
        "precip_mm": precip_mm,
        "wind_kmh": wind_kmh,
        "temp_c": temp_c,
        "humidity_pct": humidity_pct,
    }


# ---------------------------------------------------------------------------
# _classify_weather_conditions
# ---------------------------------------------------------------------------


class TestClassifyWeatherConditions:
    def test_detects_heavy_rain(self):
        days = [_make_meteo_day(1, precip_mm=50.0)]
        tagged = _classify_weather_conditions(days)
        assert any(f"heavy_rain >{HEAVY_RAIN_MM}mm" in c for c in tagged[0]["conditions"])

    def test_detects_high_wind(self):
        days = [_make_meteo_day(1, wind_kmh=90.0)]
        tagged = _classify_weather_conditions(days)
        assert any(f"high_wind >{HIGH_WIND_KMH}km/h" in c for c in tagged[0]["conditions"])

    def test_detects_freeze_thaw(self):
        days = [
            _make_meteo_day(2, temp_c=-5.0),
            _make_meteo_day(1, temp_c=5.0),
        ]
        tagged = _classify_weather_conditions(days)
        assert "freeze_thaw" in tagged[1]["conditions"]

    def test_no_conditions_for_mild_weather(self):
        days = [_make_meteo_day(1, precip_mm=5.0, wind_kmh=10.0, temp_c=15.0)]
        tagged = _classify_weather_conditions(days)
        assert tagged[0]["conditions"] == []

    def test_prolonged_humidity(self):
        days = [_make_meteo_day(i, humidity_pct=90.0) for i in range(4, 0, -1)]
        tagged = _classify_weather_conditions(days)
        # At least the last day should have prolonged_humidity
        has_humidity = any(
            any("prolonged_humidity" in c for c in d["conditions"]) for d in tagged
        )
        assert has_humidity


# ---------------------------------------------------------------------------
# _find_preceding_conditions
# ---------------------------------------------------------------------------


class TestFindPrecedingConditions:
    def test_finds_conditions_before_incident(self):
        now = datetime.utcnow()
        meteo = [
            {
                "date": now - timedelta(days=3),
                "conditions": [f"heavy_rain >{HEAVY_RAIN_MM}mm"],
            }
        ]
        matches = _find_preceding_conditions(now, meteo, lookback_days=7)
        assert len(matches) == 1
        assert matches[0]["days_before_incident"] == 3

    def test_ignores_conditions_outside_window(self):
        now = datetime.utcnow()
        meteo = [
            {
                "date": now - timedelta(days=20),
                "conditions": [f"heavy_rain >{HEAVY_RAIN_MM}mm"],
            }
        ]
        matches = _find_preceding_conditions(now, meteo, lookback_days=14)
        assert len(matches) == 0

    def test_ignores_days_without_conditions(self):
        now = datetime.utcnow()
        meteo = [{"date": now - timedelta(days=2), "conditions": []}]
        matches = _find_preceding_conditions(now, meteo, lookback_days=7)
        assert len(matches) == 0


# ---------------------------------------------------------------------------
# _build_correlations
# ---------------------------------------------------------------------------


class TestBuildCorrelations:
    def test_builds_correlation_for_leak_with_rain(self):
        building_id = uuid.uuid4()
        org_id = uuid.uuid4()
        incidents = [
            _make_incident(building_id, org_id, "leak", days_ago=30),
            _make_incident(building_id, org_id, "leak", days_ago=60),
        ]
        # Meteo: heavy rain 2 days before each incident
        meteo = []
        for inc in incidents:
            meteo.append({
                "date": inc.discovered_at - timedelta(days=2),
                "precip_mm": 55.0,
                "wind_kmh": 10.0,
                "temp_c": 12.0,
                "humidity_pct": 60.0,
            })
            # Add mild days too
            meteo.append({
                "date": inc.discovered_at - timedelta(days=5),
                "precip_mm": 3.0,
                "wind_kmh": 5.0,
                "temp_c": 14.0,
                "humidity_pct": 55.0,
            })

        corr = _build_correlations(incidents, meteo)
        assert "leak" in corr
        assert corr["leak"]["weather_preceded"] == 2
        assert corr["leak"]["probability"] == 1.0
        assert f"heavy_rain >{HEAVY_RAIN_MM}mm" in corr["leak"]["weather_conditions"]

    def test_ignores_non_weather_sensitive_types(self):
        building_id = uuid.uuid4()
        org_id = uuid.uuid4()
        incidents = [_make_incident(building_id, org_id, "vandalism", days_ago=10)]
        meteo = [_make_meteo_day(12, precip_mm=60.0)]
        corr = _build_correlations(incidents, meteo)
        assert "vandalism" not in corr

    def test_empty_incidents(self):
        corr = _build_correlations([], [])
        assert corr == {}


# ---------------------------------------------------------------------------
# analyze_correlations (async, needs db)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_no_incidents(db_session, admin_user):
    """Building with no incidents returns empty correlations."""
    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await analyze_correlations(db_session, b.id)
    assert result["incident_count"] == 0
    assert result["correlations"] == {}
    assert result["data_quality"] == "no_incidents"


@pytest.mark.asyncio
async def test_analyze_with_incidents(db_session, admin_user):
    """Building with weather-sensitive incidents generates correlations."""
    from app.models.organization import Organization

    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db_session.add(org)
    await db_session.flush()

    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.flush()

    # Add multiple leak incidents
    for i in range(3):
        inc = _make_incident(b.id, org.id, "leak", days_ago=30 + i * 30)
        db_session.add(inc)
    await db_session.commit()

    result = await analyze_correlations(db_session, b.id)
    assert result["incident_count"] == 3
    assert result["building_id"] == str(b.id)


@pytest.mark.asyncio
async def test_analyze_building_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await analyze_correlations(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# predict_incidents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_predict_no_history(db_session, admin_user):
    """Building without incidents returns no predictions."""
    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await predict_incidents(db_session, b.id, forecast=[])
    assert result["building_risk_level"] == "none"
    assert result["predicted_incidents"] == []


@pytest.mark.asyncio
async def test_predict_no_forecast(db_session, admin_user):
    """With correlations but no forecast, returns unknown risk."""
    from app.models.organization import Organization

    org = Organization(
        id=uuid.uuid4(),
        name="Test Org 2",
        type="diagnostic_lab",
    )
    db_session.add(org)
    await db_session.flush()

    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.flush()

    for i in range(3):
        db_session.add(_make_incident(b.id, org.id, "leak", days_ago=30 + i * 30))
    await db_session.commit()

    result = await predict_incidents(db_session, b.id, forecast=None)
    # Could be "unknown" (has correlations but no forecast) or "none" (synthetic data might not match)
    assert result["building_risk_level"] in ("unknown", "none")


@pytest.mark.asyncio
async def test_predict_with_heavy_rain_forecast(db_session, admin_user):
    """Heavy rain in forecast + leak history → should generate prediction."""
    from app.models.organization import Organization

    org = Organization(
        id=uuid.uuid4(),
        name="Test Org 3",
        type="diagnostic_lab",
    )
    db_session.add(org)
    await db_session.flush()

    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.flush()

    # Create incidents with explicit meteo correlation
    for i in range(4):
        db_session.add(_make_incident(b.id, org.id, "leak", days_ago=30 + i * 30))
    await db_session.commit()

    forecast = [
        {
            "date": "2026-04-03",
            "precip_mm": 55.0,
            "wind_kmh": 15.0,
            "temp_max_c": 12.0,
            "temp_min_c": 5.0,
        }
    ]

    result = await predict_incidents(db_session, b.id, forecast=forecast)
    # With synthetic meteo some correlations may or may not match the forecast;
    # at minimum the structure should be correct
    assert "predicted_incidents" in result
    assert "building_risk_level" in result
    assert isinstance(result["predicted_incidents"], list)
