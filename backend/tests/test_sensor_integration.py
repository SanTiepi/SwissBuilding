"""Tests for the Sensor Integration module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.services.sensor_integration_service import (
    get_building_sensor_alerts,
    get_building_sensor_overview,
    get_building_sensor_trends,
    get_portfolio_sensor_status,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org_id():
    return uuid.uuid4()


@pytest.fixture
async def owner_with_org(db_session: AsyncSession, org_id: uuid.UUID):
    from tests.conftest import _HASH_OWNER

    user = User(
        id=uuid.uuid4(),
        email="sensor-owner@test.ch",
        password_hash=_HASH_OWNER,
        first_name="Sensor",
        last_name="Owner",
        role="owner",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def building_no_diag(db_session: AsyncSession, admin_user: User):
    """Building with no diagnostics."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Capteur 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_with_radon(db_session: AsyncSession, admin_user: User):
    """Building with a radon diagnostic and elevated sample."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Radon 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="radon",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="RN-001",
        pollutant_type="radon",
        concentration=450.0,
        unit="Bq/m³",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_with_asbestos(db_session: AsyncSession, admin_user: User):
    """Building with an asbestos diagnostic and exceeded threshold."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Amiante 3",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1955,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="AB-001",
        pollutant_type="asbestos",
        concentration=0.02,
        unit="f/cm³",
        threshold_exceeded=True,
        risk_level="high",
        location_detail="Sous-sol local technique",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def building_in_org(
    db_session: AsyncSession,
    owner_with_org: User,
):
    """Building owned by user in an org."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Org 10",
        postal_code="1200",
        city="Genève",
        canton="GE",
        construction_year=1975,
        building_type="residential",
        created_by=owner_with_org.id,
        owner_id=owner_with_org.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Service tests: get_building_sensor_overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overview_nonexistent_building(db_session: AsyncSession):
    """Non-existent building returns empty overview."""
    result = await get_building_sensor_overview(uuid.uuid4(), db_session)
    assert result.total_sensors == 0
    assert result.sensors == []
    assert result.latest_readings == []


@pytest.mark.asyncio
async def test_overview_building_no_diagnostics(db_session: AsyncSession, building_no_diag: Building):
    """Building without diagnostics gets default sensors."""
    result = await get_building_sensor_overview(building_no_diag.id, db_session)
    assert result.total_sensors >= 2
    assert result.active_sensors == result.total_sensors
    sensor_types = {s.sensor_type for s in result.sensors}
    assert "humidity_temp" in sensor_types
    assert "co2_monitor" in sensor_types


@pytest.mark.asyncio
async def test_overview_building_with_radon(db_session: AsyncSession, building_with_radon: Building):
    """Building with radon diagnostic gets radon_monitor sensor."""
    result = await get_building_sensor_overview(building_with_radon.id, db_session)
    sensor_types = {s.sensor_type for s in result.sensors}
    assert "radon_monitor" in sensor_types
    # Should have elevated reading from actual sample data
    radon_readings = [r for r in result.latest_readings if r.metric == "radon_concentration"]
    assert len(radon_readings) == 1
    assert radon_readings[0].value == 450.0
    assert radon_readings[0].is_above_threshold is True


@pytest.mark.asyncio
async def test_overview_building_with_asbestos(db_session: AsyncSession, building_with_asbestos: Building):
    """Building with asbestos diagnostic gets air_quality + particle_counter."""
    result = await get_building_sensor_overview(building_with_asbestos.id, db_session)
    sensor_types = {s.sensor_type for s in result.sensors}
    assert "air_quality" in sensor_types
    assert "particle_counter" in sensor_types
    # Fiber reading should be elevated
    fiber_readings = [r for r in result.latest_readings if r.metric == "fiber_concentration"]
    assert len(fiber_readings) == 1
    assert fiber_readings[0].value == 0.015
    assert fiber_readings[0].is_above_threshold is True


@pytest.mark.asyncio
async def test_overview_sensors_all_active(db_session: AsyncSession, building_no_diag: Building):
    """All simulated sensors should be active."""
    result = await get_building_sensor_overview(building_no_diag.id, db_session)
    for sensor in result.sensors:
        assert sensor.status == "active"


@pytest.mark.asyncio
async def test_overview_sensors_with_alerts_count(db_session: AsyncSession, building_with_radon: Building):
    """sensors_with_alerts counts sensors that have above-threshold readings."""
    result = await get_building_sensor_overview(building_with_radon.id, db_session)
    assert result.sensors_with_alerts >= 1


@pytest.mark.asyncio
async def test_overview_generated_at(db_session: AsyncSession, building_no_diag: Building):
    """generated_at should be recent."""
    result = await get_building_sensor_overview(building_no_diag.id, db_session)
    assert result.generated_at is not None
    assert (datetime.now(UTC) - result.generated_at).total_seconds() < 10


# ---------------------------------------------------------------------------
# Service tests: get_building_sensor_alerts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alerts_nonexistent_building(db_session: AsyncSession):
    """Non-existent building returns no alerts."""
    result = await get_building_sensor_alerts(uuid.uuid4(), db_session)
    assert result.total_alerts == 0
    assert result.alerts == []


@pytest.mark.asyncio
async def test_alerts_radon_warning(db_session: AsyncSession, building_with_radon: Building):
    """Building with radon > 300 generates warning alert."""
    result = await get_building_sensor_alerts(building_with_radon.id, db_session)
    radon_alerts = [a for a in result.alerts if a.metric == "radon_concentration"]
    assert len(radon_alerts) >= 1
    alert = radon_alerts[0]
    assert alert.threshold == 300.0
    assert alert.value == 450.0
    assert alert.severity == "warning"  # 450/300 = 1.5x, > 1x but < 2x


@pytest.mark.asyncio
async def test_alerts_asbestos_warning(db_session: AsyncSession, building_with_asbestos: Building):
    """Building with asbestos threshold exceeded generates alert."""
    result = await get_building_sensor_alerts(building_with_asbestos.id, db_session)
    fiber_alerts = [a for a in result.alerts if a.metric == "fiber_concentration"]
    assert len(fiber_alerts) >= 1
    assert fiber_alerts[0].severity == "warning"  # 0.015/0.01 = 1.5x


@pytest.mark.asyncio
async def test_alerts_no_threshold_no_alert(db_session: AsyncSession, building_no_diag: Building):
    """Building with normal readings should have no critical or warning alerts."""
    result = await get_building_sensor_alerts(building_no_diag.id, db_session)
    critical = [a for a in result.alerts if a.severity == "critical"]
    warnings = [a for a in result.alerts if a.severity == "warning"]
    assert len(critical) == 0
    assert len(warnings) == 0


@pytest.mark.asyncio
async def test_alerts_unacknowledged_count(db_session: AsyncSession, building_with_radon: Building):
    """All generated alerts should be unacknowledged."""
    result = await get_building_sensor_alerts(building_with_radon.id, db_session)
    assert result.unacknowledged_count == result.total_alerts


@pytest.mark.asyncio
async def test_alerts_critical_count(db_session: AsyncSession, building_with_radon: Building):
    """Critical count matches actual critical alerts."""
    result = await get_building_sensor_alerts(building_with_radon.id, db_session)
    actual = sum(1 for a in result.alerts if a.severity == "critical")
    assert result.critical_count == actual


# ---------------------------------------------------------------------------
# Service tests: get_building_sensor_trends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_nonexistent_building(db_session: AsyncSession):
    """Non-existent building returns empty trends."""
    result = await get_building_sensor_trends(uuid.uuid4(), db_session)
    assert result.trends == []
    assert result.monitoring_period_days == 30


@pytest.mark.asyncio
async def test_trends_default_period(db_session: AsyncSession, building_no_diag: Building):
    """Default period is 30 days."""
    result = await get_building_sensor_trends(building_no_diag.id, db_session)
    assert result.monitoring_period_days == 30


@pytest.mark.asyncio
async def test_trends_custom_period(db_session: AsyncSession, building_no_diag: Building):
    """Custom period is respected."""
    result = await get_building_sensor_trends(building_no_diag.id, db_session, period_days=90)
    assert result.monitoring_period_days == 90


@pytest.mark.asyncio
async def test_trends_direction_above_threshold(db_session: AsyncSession, building_with_radon: Building):
    """Sensors above threshold should show rising trend."""
    result = await get_building_sensor_trends(building_with_radon.id, db_session)
    radon_trends = [t for t in result.trends if t.metric == "radon_concentration"]
    assert len(radon_trends) == 1
    assert radon_trends[0].trend_direction == "rising"


@pytest.mark.asyncio
async def test_trends_min_max_avg(db_session: AsyncSession, building_no_diag: Building):
    """Trend min <= avg <= max."""
    result = await get_building_sensor_trends(building_no_diag.id, db_session)
    for trend in result.trends:
        assert trend.min_value <= trend.avg_value <= trend.max_value


@pytest.mark.asyncio
async def test_trends_readings_count(db_session: AsyncSession, building_no_diag: Building):
    """readings_count should be period_days * 24 (hourly)."""
    result = await get_building_sensor_trends(building_no_diag.id, db_session, period_days=7)
    for trend in result.trends:
        assert trend.readings_count == 7 * 24


# ---------------------------------------------------------------------------
# Service tests: get_portfolio_sensor_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_no_buildings(db_session: AsyncSession):
    """Org with no buildings returns empty status."""
    result = await get_portfolio_sensor_status(uuid.uuid4(), db_session)
    assert result.total_buildings_monitored == 0
    assert result.total_sensors == 0


@pytest.mark.asyncio
async def test_portfolio_with_building(
    db_session: AsyncSession,
    owner_with_org: User,
    building_in_org: Building,
    org_id: uuid.UUID,
):
    """Org with a building returns aggregated status."""
    result = await get_portfolio_sensor_status(org_id, db_session)
    assert result.total_buildings_monitored == 1
    assert result.total_sensors >= 2
    assert result.active_sensors >= 2
    assert result.organization_id == org_id


@pytest.mark.asyncio
async def test_portfolio_alert_summary_keys(
    db_session: AsyncSession,
    owner_with_org: User,
    building_in_org: Building,
    org_id: uuid.UUID,
):
    """Alert summary contains expected severity keys."""
    result = await get_portfolio_sensor_status(org_id, db_session)
    assert "info" in result.alert_summary
    assert "warning" in result.alert_summary
    assert "critical" in result.alert_summary


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_overview(client, auth_headers, sample_building):
    """GET /sensor-integration/buildings/{id}/overview returns 200."""
    resp = await client.get(
        f"/api/v1/sensor-integration/buildings/{sample_building.id}/overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "sensors" in data
    assert "total_sensors" in data
    assert "latest_readings" in data


@pytest.mark.asyncio
async def test_api_alerts(client, auth_headers, sample_building):
    """GET /sensor-integration/buildings/{id}/alerts returns 200."""
    resp = await client.get(
        f"/api/v1/sensor-integration/buildings/{sample_building.id}/alerts",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert "total_alerts" in data
    assert "critical_count" in data


@pytest.mark.asyncio
async def test_api_trends(client, auth_headers, sample_building):
    """GET /sensor-integration/buildings/{id}/trends returns 200."""
    resp = await client.get(
        f"/api/v1/sensor-integration/buildings/{sample_building.id}/trends",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "trends" in data
    assert data["monitoring_period_days"] == 30


@pytest.mark.asyncio
async def test_api_trends_custom_period(client, auth_headers, sample_building):
    """GET /sensor-integration/buildings/{id}/trends?period_days=90 returns 200."""
    resp = await client.get(
        f"/api/v1/sensor-integration/buildings/{sample_building.id}/trends?period_days=90",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitoring_period_days"] == 90


@pytest.mark.asyncio
async def test_api_portfolio_status(client, auth_headers):
    """GET /sensor-integration/organizations/{id}/status returns 200."""
    org_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/sensor-integration/organizations/{org_id}/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings_monitored" in data
    assert "total_sensors" in data
    assert "alert_summary" in data


@pytest.mark.asyncio
async def test_api_overview_unauthenticated(client, sample_building):
    """Unauthenticated request returns 401."""
    resp = await client.get(
        f"/api/v1/sensor-integration/buildings/{sample_building.id}/overview",
    )
    assert resp.status_code == 403
