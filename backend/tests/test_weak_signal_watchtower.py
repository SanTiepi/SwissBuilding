"""Tests for the Weak Signal Watchtower service and API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.building_change import BuildingSignal
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue
from app.services.weak_signal_watchtower import (
    get_buildings_on_critical_path,
    get_signal_history,
    get_watch_rules,
    scan_building_weak_signals,
    scan_portfolio_weak_signals,
)

# ── Helpers ─────────────────────────────────────────────────────────


def _make_building(admin_id: uuid.UUID, **kwargs) -> Building:
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": admin_id,
        "status": "active",
    }
    defaults.update(kwargs)
    return Building(**defaults)


def _make_snapshot(building_id: uuid.UUID, **kwargs) -> BuildingSnapshot:
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "snapshot_type": "manual",
        "captured_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return BuildingSnapshot(**defaults)


def _make_diagnostic(building_id: uuid.UUID, **kwargs) -> Diagnostic:
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
    }
    defaults.update(kwargs)
    return Diagnostic(**defaults)


def _make_intervention(building_id: uuid.UUID, **kwargs) -> Intervention:
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "removal",
        "title": "Test intervention",
        "status": "completed",
    }
    defaults.update(kwargs)
    return Intervention(**defaults)


def _make_unknown(building_id: uuid.UUID, **kwargs) -> UnknownIssue:
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "unknown_type": "missing_data",
        "severity": "medium",
        "status": "open",
        "title": "Unknown issue",
    }
    defaults.update(kwargs)
    return UnknownIssue(**defaults)


def _make_change_signal(building_id: uuid.UUID, **kwargs) -> BuildingSignal:
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "signal_type": "trust_erosion",
        "severity": "medium",
        "title": "Test change signal",
        "description": "",
        "based_on_type": "event",
        "status": "active",
        "detected_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return BuildingSignal(**defaults)


# ── Service Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_data_produces_no_signals(db_session, admin_user):
    """Building with no data should produce zero signals."""
    building = _make_building(admin_user.id)
    db_session.add(building)
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    assert report.total_signals == 0
    assert report.signals == []
    assert report.risk_trajectory == "stable"
    assert report.highest_severity == "watch"


@pytest.mark.asyncio
async def test_trust_erosion_detected(db_session, admin_user):
    """Trust score < 0.6 and declining should trigger trust_erosion."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    # Previous snapshot with higher trust
    snap_old = _make_snapshot(
        building.id,
        overall_trust=0.7,
        captured_at=datetime.now(UTC) - timedelta(days=30),
    )
    # Latest snapshot with lower trust
    snap_new = _make_snapshot(
        building.id,
        overall_trust=0.45,
        captured_at=datetime.now(UTC),
    )
    db_session.add_all([snap_old, snap_new])
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "trust_erosion" in types

    trust_signal = next(s for s in report.signals if s.signal_type == "trust_erosion")
    assert trust_signal.confidence > 0
    assert trust_signal.metadata["current_trust"] == 0.45


@pytest.mark.asyncio
async def test_trust_erosion_not_triggered_when_above_threshold(db_session, admin_user):
    """Trust score above 0.6 should not trigger trust_erosion even if declining."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    snap_old = _make_snapshot(building.id, overall_trust=0.9, captured_at=datetime.now(UTC) - timedelta(days=30))
    snap_new = _make_snapshot(building.id, overall_trust=0.75, captured_at=datetime.now(UTC))
    db_session.add_all([snap_old, snap_new])
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "trust_erosion" not in types


@pytest.mark.asyncio
async def test_completeness_decay_detected(db_session, admin_user):
    """Completeness drop between snapshots should trigger completeness_decay."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    snap_old = _make_snapshot(
        building.id,
        completeness_score=0.85,
        captured_at=datetime.now(UTC) - timedelta(days=15),
    )
    snap_new = _make_snapshot(
        building.id,
        completeness_score=0.60,
        captured_at=datetime.now(UTC),
    )
    db_session.add_all([snap_old, snap_new])
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "completeness_decay" in types


@pytest.mark.asyncio
async def test_completeness_no_decay_when_improving(db_session, admin_user):
    """Completeness improving should not trigger completeness_decay."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    snap_old = _make_snapshot(building.id, completeness_score=0.60, captured_at=datetime.now(UTC) - timedelta(days=15))
    snap_new = _make_snapshot(building.id, completeness_score=0.85, captured_at=datetime.now(UTC))
    db_session.add_all([snap_old, snap_new])
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "completeness_decay" not in types


@pytest.mark.asyncio
async def test_diagnostic_aging_detected(db_session, admin_user):
    """Diagnostic older than 3 years triggers diagnostic_aging."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    old_diag = _make_diagnostic(
        building.id,
        date_report=datetime.now(UTC).date() - timedelta(days=4 * 365),
    )
    db_session.add(old_diag)
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "diagnostic_aging" in types


@pytest.mark.asyncio
async def test_diagnostic_aging_not_triggered_with_recent_diagnostic(db_session, admin_user):
    """Old diagnostic with a recent renewal should not trigger."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    old_diag = _make_diagnostic(building.id, date_report=datetime.now(UTC).date() - timedelta(days=4 * 365))
    new_diag = _make_diagnostic(building.id, date_report=datetime.now(UTC).date() - timedelta(days=30))
    db_session.add_all([old_diag, new_diag])
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "diagnostic_aging" not in types


@pytest.mark.asyncio
async def test_intervention_stall_detected(db_session, admin_user):
    """Intervention in_progress > 90 days should trigger intervention_stall."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    stalled = _make_intervention(
        building.id,
        status="in_progress",
        created_at=datetime.now(UTC) - timedelta(days=120),
    )
    db_session.add(stalled)
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "intervention_stall" in types


@pytest.mark.asyncio
async def test_intervention_stall_not_triggered_under_90_days(db_session, admin_user):
    """Intervention in_progress for < 90 days should not trigger."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    recent = _make_intervention(
        building.id,
        status="in_progress",
        created_at=datetime.now(UTC) - timedelta(days=30),
    )
    db_session.add(recent)
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "intervention_stall" not in types


@pytest.mark.asyncio
async def test_evidence_gap_widening_detected(db_session, admin_user):
    """More than 3 open unknowns should trigger evidence_gap_widening."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    for _ in range(4):
        db_session.add(_make_unknown(building.id))
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "evidence_gap_widening" in types


@pytest.mark.asyncio
async def test_evidence_gap_not_triggered_with_few_unknowns(db_session, admin_user):
    """3 or fewer open unknowns should not trigger."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    for _ in range(3):
        db_session.add(_make_unknown(building.id))
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "evidence_gap_widening" not in types


@pytest.mark.asyncio
async def test_grade_risk_detected(db_session, admin_user):
    """Grade D with no active intervention triggers grade_risk."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    snap = _make_snapshot(building.id, passport_grade="D", captured_at=datetime.now(UTC))
    db_session.add(snap)
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "grade_risk" in types

    grade_signal = next(s for s in report.signals if s.signal_type == "grade_risk")
    assert grade_signal.severity == "warning"


@pytest.mark.asyncio
async def test_grade_risk_not_triggered_with_active_intervention(db_session, admin_user):
    """Grade D with active intervention should not trigger."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    snap = _make_snapshot(building.id, passport_grade="D", captured_at=datetime.now(UTC))
    interv = _make_intervention(building.id, status="planned")
    db_session.add_all([snap, interv])
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "grade_risk" not in types


@pytest.mark.asyncio
async def test_unknown_accumulation_detected(db_session, admin_user):
    """5+ open high/critical unknowns should trigger unknown_accumulation."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    for _ in range(5):
        db_session.add(_make_unknown(building.id, severity="high"))
    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    types = [s.signal_type for s in report.signals]
    assert "unknown_accumulation" in types


@pytest.mark.asyncio
async def test_multiple_signals_on_same_building(db_session, admin_user):
    """A building can trigger multiple signals simultaneously."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    # Trust erosion setup
    snap_old = _make_snapshot(building.id, overall_trust=0.7, captured_at=datetime.now(UTC) - timedelta(days=30))
    snap_new = _make_snapshot(building.id, overall_trust=0.4, passport_grade="E", captured_at=datetime.now(UTC))
    db_session.add_all([snap_old, snap_new])

    # Old diagnostic
    old_diag = _make_diagnostic(building.id, date_report=datetime.now(UTC).date() - timedelta(days=4 * 365))
    db_session.add(old_diag)

    # Stalled intervention
    stalled = _make_intervention(building.id, status="in_progress", created_at=datetime.now(UTC) - timedelta(days=120))
    db_session.add(stalled)

    await db_session.commit()

    report = await scan_building_weak_signals(db_session, building.id)
    assert report.total_signals >= 3
    assert report.risk_trajectory == "critical_path"
    types = {s.signal_type for s in report.signals}
    assert "trust_erosion" in types
    assert "diagnostic_aging" in types
    assert "intervention_stall" in types


@pytest.mark.asyncio
async def test_portfolio_scan_aggregation(db_session, admin_user):
    """Portfolio scan should aggregate signals across buildings."""
    # Building 1: has trust erosion
    b1 = _make_building(admin_user.id, address="Rue A 1")
    db_session.add(b1)
    snap1_old = _make_snapshot(b1.id, overall_trust=0.7, captured_at=datetime.now(UTC) - timedelta(days=30))
    snap1_new = _make_snapshot(b1.id, overall_trust=0.4, captured_at=datetime.now(UTC))
    db_session.add_all([snap1_old, snap1_new])

    # Building 2: no issues
    b2 = _make_building(admin_user.id, address="Rue B 2")
    db_session.add(b2)

    await db_session.commit()

    report = await scan_portfolio_weak_signals(db_session)
    assert report.total_buildings_scanned == 2
    assert report.buildings_with_signals == 1
    assert "trust_erosion" in report.signals_by_type


@pytest.mark.asyncio
async def test_critical_path_detection(db_session, admin_user):
    """Buildings with 3+ signals should appear on critical path."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    # Setup multiple signal triggers
    snap_old = _make_snapshot(building.id, overall_trust=0.7, captured_at=datetime.now(UTC) - timedelta(days=30))
    snap_new = _make_snapshot(building.id, overall_trust=0.4, passport_grade="D", captured_at=datetime.now(UTC))
    db_session.add_all([snap_old, snap_new])

    old_diag = _make_diagnostic(building.id, date_report=datetime.now(UTC).date() - timedelta(days=4 * 365))
    db_session.add(old_diag)

    stalled = _make_intervention(building.id, status="in_progress", created_at=datetime.now(UTC) - timedelta(days=120))
    db_session.add(stalled)

    await db_session.commit()

    critical = await get_buildings_on_critical_path(db_session)
    assert len(critical) >= 1
    assert critical[0]["signal_count"] >= 3


@pytest.mark.asyncio
async def test_watch_rules_listing():
    """get_watch_rules should return all 7 rules."""
    rules = get_watch_rules()
    assert len(rules) == 7
    rule_types = {r.rule_type for r in rules}
    assert "trust_erosion" in rule_types
    assert "completeness_decay" in rule_types
    assert "diagnostic_aging" in rule_types
    assert "intervention_stall" in rule_types
    assert "evidence_gap_widening" in rule_types
    assert "grade_risk" in rule_types
    assert "unknown_accumulation" in rule_types
    assert all(r.enabled for r in rules)


@pytest.mark.asyncio
async def test_signal_history_from_change_signals(db_session, admin_user):
    """Signal history should map relevant BuildingSignals to WeakSignals."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    cs = _make_change_signal(
        building.id,
        signal_type="trust_erosion",
        severity="high",
        detected_at=datetime.now(UTC) - timedelta(days=10),
    )
    db_session.add(cs)
    await db_session.commit()

    history = await get_signal_history(db_session, building.id, days=90)
    assert len(history) >= 1
    assert history[0].signal_type == "trust_erosion"
    assert history[0].severity == "warning"  # high maps to warning


@pytest.mark.asyncio
async def test_signal_history_excludes_old_signals(db_session, admin_user):
    """Signals older than the requested window should be excluded."""
    building = _make_building(admin_user.id)
    db_session.add(building)

    old_cs = _make_change_signal(
        building.id,
        signal_type="trust_erosion",
        severity="medium",
        detected_at=datetime.now(UTC) - timedelta(days=100),
    )
    db_session.add(old_cs)
    await db_session.commit()

    history = await get_signal_history(db_session, building.id, days=90)
    assert len(history) == 0


# ── API Endpoint Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_building_weak_signals(client, auth_headers, sample_building):
    """GET /buildings/{id}/weak-signals should return a report."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/weak-signals", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "signals" in data
    assert "total_signals" in data
    assert "risk_trajectory" in data


@pytest.mark.asyncio
async def test_api_building_weak_signals_404(client, auth_headers):
    """GET /buildings/{nonexistent}/weak-signals should return 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/weak-signals", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_portfolio_weak_signals(client, auth_headers, sample_building):
    """GET /portfolio/weak-signals should return a portfolio report."""
    resp = await client.get("/api/v1/portfolio/weak-signals", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings_scanned" in data
    assert "signals_by_type" in data


@pytest.mark.asyncio
async def test_api_critical_path(client, auth_headers, sample_building):
    """GET /portfolio/critical-path should return a list."""
    resp = await client.get("/api/v1/portfolio/critical-path", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_weak_signal_history(client, auth_headers, sample_building):
    """GET /buildings/{id}/weak-signals/history should return a list."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/weak-signals/history", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_watch_rules(client, auth_headers):
    """GET /weak-signals/rules should return 7 rules."""
    resp = await client.get("/api/v1/weak-signals/rules", headers=auth_headers)
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 7


@pytest.mark.asyncio
async def test_api_requires_auth(client):
    """Endpoints should require authentication."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/weak-signals")
    assert resp.status_code == 401
