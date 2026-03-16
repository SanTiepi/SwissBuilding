"""Tests for anomaly detection service and API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.anomaly_detection_service import (
    detect_anomalies,
    detect_portfolio_anomalies,
    get_anomaly_trend,
    get_critical_anomalies,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _building(admin_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_id,
        status="active",
    )
    defaults.update(kw)
    return Building(**defaults)


def _diagnostic(building_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="draft",
        created_at=datetime.now(UTC),
    )
    defaults.update(kw)
    return Diagnostic(**defaults)


def _sample(diagnostic_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
    )
    defaults.update(kw)
    return Sample(**defaults)


def _zone(building_id, admin_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="room",
        name="Room 1",
        created_by=admin_id,
    )
    defaults.update(kw)
    return Zone(**defaults)


def _snapshot(building_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        building_id=building_id,
        snapshot_type="manual",
        captured_at=datetime.now(UTC),
    )
    defaults.update(kw)
    return BuildingSnapshot(**defaults)


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_building(db_session, admin_user):
    """Empty building with no data returns empty anomaly report."""
    b = _building(admin_user.id, construction_year=2005)
    db_session.add(b)
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    assert report.building_id == b.id
    assert report.total == 0
    assert report.anomalies == []


@pytest.mark.asyncio
async def test_nonexistent_building(db_session):
    """Nonexistent building returns empty report."""
    fake_id = uuid.uuid4()
    report = await detect_anomalies(db_session, fake_id)
    assert report.total == 0


@pytest.mark.asyncio
async def test_value_spike_detection(db_session, admin_user):
    """Detects sample with concentration >10x average."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    diag = _diagnostic(b.id, status="completed")
    db_session.add(diag)
    await db_session.flush()

    # Spike must be >10x the average (which includes the spike itself).
    # With 19 samples at 1.0 and 1 at 500: avg = 25.95, 500 > 259.5 => spike.
    for _ in range(19):
        db_session.add(_sample(diag.id, pollutant_type="hap", concentration=1.0, unit="mg/kg"))
    db_session.add(_sample(diag.id, pollutant_type="hap", concentration=500.0, unit="mg/kg"))
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    spike_anomalies = [a for a in report.anomalies if a.anomaly_type.value == "value_spike"]
    assert len(spike_anomalies) >= 1
    assert spike_anomalies[0].severity.value == "warning"


@pytest.mark.asyncio
async def test_no_value_spike_when_similar(db_session, admin_user):
    """No spike when all concentrations are similar."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    diag = _diagnostic(b.id, status="completed")
    db_session.add(diag)
    await db_session.flush()

    for _ in range(4):
        db_session.add(_sample(diag.id, pollutant_type="pcb", concentration=10.0, unit="mg/kg"))
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    spike_anomalies = [a for a in report.anomalies if a.anomaly_type.value == "value_spike"]
    assert len(spike_anomalies) == 0


@pytest.mark.asyncio
async def test_missing_data_detection(db_session, admin_user):
    """Detects low sample coverage across zones."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    # 5 zones, 0 samples -> coverage = 0%
    for i in range(5):
        db_session.add(_zone(b.id, admin_user.id, name=f"Zone {i}"))
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    missing = [a for a in report.anomalies if a.anomaly_type.value == "missing_data"]
    assert len(missing) == 1
    assert missing[0].severity.value == "warning"


@pytest.mark.asyncio
async def test_no_missing_data_with_enough_samples(db_session, admin_user):
    """No missing data anomaly when sample count >= zone count."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    for i in range(3):
        db_session.add(_zone(b.id, admin_user.id, name=f"Zone {i}"))

    diag = _diagnostic(b.id)
    db_session.add(diag)
    await db_session.flush()

    for _i in range(3):
        db_session.add(_sample(diag.id, pollutant_type="asbestos", concentration=0.05))
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    missing = [a for a in report.anomalies if a.anomaly_type.value == "missing_data"]
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_inconsistent_state_detection(db_session, admin_user):
    """Detects completed diagnostic with unknown risk level."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    diag = _diagnostic(b.id, status="completed")
    db_session.add(diag)

    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=b.id,
        overall_risk_level="unknown",
    )
    db_session.add(risk)
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    inconsistent = [a for a in report.anomalies if a.anomaly_type.value == "inconsistent_state"]
    assert len(inconsistent) == 1


@pytest.mark.asyncio
async def test_no_inconsistent_state_when_risk_set(db_session, admin_user):
    """No inconsistency when risk level is set after diagnostic completion."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    diag = _diagnostic(b.id, status="completed")
    db_session.add(diag)

    risk = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=b.id,
        overall_risk_level="high",
    )
    db_session.add(risk)
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    inconsistent = [a for a in report.anomalies if a.anomaly_type.value == "inconsistent_state"]
    assert len(inconsistent) == 0


@pytest.mark.asyncio
async def test_temporal_gap_detection(db_session, admin_user):
    """Detects diagnostic gap for pre-1991 building."""
    b = _building(admin_user.id, construction_year=1960)
    db_session.add(b)
    await db_session.flush()

    # Old diagnostic only
    old_diag = _diagnostic(
        b.id,
        status="completed",
        created_at=datetime.now(UTC) - timedelta(days=4 * 365),
    )
    db_session.add(old_diag)
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    gaps = [a for a in report.anomalies if a.anomaly_type.value == "temporal_gap"]
    assert len(gaps) == 1
    assert gaps[0].severity.value == "critical"


@pytest.mark.asyncio
async def test_no_temporal_gap_for_new_building(db_session, admin_user):
    """No temporal gap for post-1991 building."""
    b = _building(admin_user.id, construction_year=2005)
    db_session.add(b)
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    gaps = [a for a in report.anomalies if a.anomaly_type.value == "temporal_gap"]
    assert len(gaps) == 0


@pytest.mark.asyncio
async def test_threshold_breach_detection(db_session, admin_user):
    """Detects samples exceeding Swiss regulatory thresholds."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    diag = _diagnostic(b.id)
    db_session.add(diag)
    await db_session.flush()

    # Asbestos > 0.1%
    db_session.add(_sample(diag.id, pollutant_type="asbestos", concentration=0.5, unit="%"))
    # PCB > 50 mg/kg
    db_session.add(_sample(diag.id, pollutant_type="pcb", concentration=120.0, unit="mg/kg"))
    # Lead under threshold
    db_session.add(_sample(diag.id, pollutant_type="lead", concentration=100.0, unit="mg/kg"))
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    breaches = [a for a in report.anomalies if a.anomaly_type.value == "threshold_breach"]
    assert len(breaches) == 2
    assert all(a.severity.value == "critical" for a in breaches)


@pytest.mark.asyncio
async def test_pattern_deviation_detection(db_session, admin_user):
    """Detects trust score drop >0.2 between snapshots."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    now = datetime.now(UTC)
    s1 = _snapshot(b.id, overall_trust=0.9, captured_at=now - timedelta(days=30))
    s2 = _snapshot(b.id, overall_trust=0.5, captured_at=now)
    db_session.add_all([s1, s2])
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    deviations = [a for a in report.anomalies if a.anomaly_type.value == "pattern_deviation"]
    assert len(deviations) == 1
    assert deviations[0].severity.value == "warning"


@pytest.mark.asyncio
async def test_no_pattern_deviation_for_small_drop(db_session, admin_user):
    """No deviation for trust drop <= 0.2."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    now = datetime.now(UTC)
    s1 = _snapshot(b.id, overall_trust=0.8, captured_at=now - timedelta(days=30))
    s2 = _snapshot(b.id, overall_trust=0.7, captured_at=now)
    db_session.add_all([s1, s2])
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    deviations = [a for a in report.anomalies if a.anomaly_type.value == "pattern_deviation"]
    assert len(deviations) == 0


@pytest.mark.asyncio
async def test_portfolio_scan(db_session, admin_user):
    """Portfolio scan returns reports for buildings with anomalies."""
    # Building with temporal gap (pre-1991, no recent diagnostic)
    b1 = _building(admin_user.id, construction_year=1960)
    # Building with no issues (post-1991)
    b2 = _building(admin_user.id, construction_year=2010)
    db_session.add_all([b1, b2])
    await db_session.commit()

    reports = await detect_portfolio_anomalies(db_session)
    # Only b1 should have anomalies (temporal gap)
    assert len(reports) >= 1
    building_ids = {r.building_id for r in reports}
    assert b1.id in building_ids


@pytest.mark.asyncio
async def test_critical_anomalies_filter(db_session, admin_user):
    """get_critical_anomalies returns only critical severity."""
    b = _building(admin_user.id, construction_year=1960)
    db_session.add(b)
    await db_session.flush()

    diag = _diagnostic(b.id)
    db_session.add(diag)
    await db_session.flush()

    # Threshold breach -> critical
    db_session.add(_sample(diag.id, pollutant_type="asbestos", concentration=5.0, unit="%"))
    await db_session.commit()

    criticals = await get_critical_anomalies(db_session)
    assert len(criticals) >= 1
    assert all(a.severity.value == "critical" for a in criticals)


@pytest.mark.asyncio
async def test_trend_computation(db_session, admin_user):
    """get_anomaly_trend returns valid trend structure."""
    b = _building(admin_user.id)
    db_session.add(b)
    await db_session.flush()

    now = datetime.now(UTC)
    for i in range(3):
        db_session.add(_snapshot(b.id, captured_at=now - timedelta(days=30 * i)))
    await db_session.commit()

    trend = await get_anomaly_trend(db_session, b.id, months=12)
    assert trend.period == "12m"
    assert trend.trend_direction in ("improving", "stable", "worsening")
    assert isinstance(trend.anomaly_counts, list)


@pytest.mark.asyncio
async def test_by_type_and_severity_counts(db_session, admin_user):
    """Report by_type and by_severity counts are accurate."""
    b = _building(admin_user.id, construction_year=1960)
    db_session.add(b)
    await db_session.flush()

    diag = _diagnostic(b.id)
    db_session.add(diag)
    await db_session.flush()

    # 1 threshold breach (critical) + temporal gap (critical)
    db_session.add(_sample(diag.id, pollutant_type="asbestos", concentration=5.0, unit="%"))
    await db_session.commit()

    report = await detect_anomalies(db_session, b.id)
    assert report.total == sum(report.by_type.values())
    assert report.total == sum(report.by_severity.values())


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_building_anomalies_404(client, auth_headers):
    """GET /buildings/{id}/anomalies returns 404 for unknown building."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/anomalies", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_building_anomalies_success(client, sample_building, auth_headers):
    """GET /buildings/{id}/anomalies returns 200 with report."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/anomalies", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "anomalies" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_api_portfolio_anomalies(client, sample_building, auth_headers):
    """GET /portfolio/anomalies returns 200."""
    resp = await client.get("/api/v1/portfolio/anomalies", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_anomaly_trend_404(client, auth_headers):
    """GET /buildings/{id}/anomalies/trend returns 404 for unknown building."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/anomalies/trend", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_anomaly_trend_success(client, sample_building, auth_headers):
    """GET /buildings/{id}/anomalies/trend returns 200."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/anomalies/trend", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "trend_direction" in data


@pytest.mark.asyncio
async def test_api_critical_anomalies(client, sample_building, auth_headers):
    """GET /portfolio/anomalies/critical returns 200."""
    resp = await client.get("/api/v1/portfolio/anomalies/critical", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
