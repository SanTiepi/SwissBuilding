"""Tests for the Predictive Readiness Service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.obligation import Obligation
from app.services.predictive_readiness_service import (
    DIAGNOSTIC_VALIDITY_DAYS,
    _detect_expiring_diagnostics,
    _detect_intervention_readiness_gaps,
    _detect_obligation_deadlines,
    _detect_readiness_degradation,
    _diagnostic_expiry_date,
    _projected_readiness,
    _readiness_status,
    scan_building,
    scan_portfolio,
)

# ── Helpers ────────────────────────────────────────────────────────


def _make_building(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": uuid.uuid4(),
        "status": "active",
    }
    defaults.update(kwargs)
    return Building(**defaults)


def _make_diagnostic(building_id, *, status="completed", date_inspection=None, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": status,
        "date_inspection": date_inspection,
    }
    defaults.update(kwargs)
    return Diagnostic(**defaults)


def _make_intervention(building_id, *, status="planned", date_start=None, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "removal",
        "title": "Removal works",
        "status": status,
        "date_start": date_start,
    }
    defaults.update(kwargs)
    return Intervention(**defaults)


def _make_obligation(building_id, *, due_date, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "title": "Test obligation",
        "obligation_type": "regulatory_inspection",
        "due_date": due_date,
        "status": "upcoming",
        "priority": "medium",
    }
    defaults.update(kwargs)
    return Obligation(**defaults)


# ── Unit tests for pure functions ──────────────────────────────────


class TestDiagnosticExpiryDate:
    def test_returns_date_inspection_plus_validity(self):
        d = _make_diagnostic(uuid.uuid4(), date_inspection=date(2023, 6, 15))
        exp = _diagnostic_expiry_date(d)
        assert exp == date(2023, 6, 15) + timedelta(days=DIAGNOSTIC_VALIDITY_DAYS)

    def test_returns_none_when_no_date(self):
        d = _make_diagnostic(uuid.uuid4())
        d.created_at = None
        exp = _diagnostic_expiry_date(d)
        assert exp is None


class TestReadinessStatus:
    def test_ready_when_valid_diagnostic(self):
        today = date.today()
        d = _make_diagnostic(uuid.uuid4(), date_inspection=today - timedelta(days=100))
        assert _readiness_status([d], today) == "ready"

    def test_not_ready_when_expired(self):
        today = date.today()
        d = _make_diagnostic(uuid.uuid4(), date_inspection=today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS + 10))
        assert _readiness_status([d], today) == "not_ready"

    def test_not_ready_when_no_diagnostics(self):
        assert _readiness_status([], date.today()) == "not_ready"


class TestProjectedReadiness:
    def test_still_ready_in_30d(self):
        today = date.today()
        d = _make_diagnostic(uuid.uuid4(), date_inspection=today - timedelta(days=100))
        assert _projected_readiness([d], today, 30) == "ready"

    def test_partial_when_expiring_in_window(self):
        today = date.today()
        # Diagnostic will expire in 60 days -> 90d projection = partial
        days_until_expiry = 60
        inspection_date = today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS - days_until_expiry)
        d = _make_diagnostic(uuid.uuid4(), date_inspection=inspection_date)
        assert _projected_readiness([d], today, 90) in ("partial", "not_ready")


class TestDetectExpiringDiagnostics:
    def test_no_alert_for_fresh_diagnostic(self):
        today = date.today()
        b = _make_building()
        d = _make_diagnostic(b.id, date_inspection=today - timedelta(days=30))
        alerts = _detect_expiring_diagnostics(b, [d], today)
        assert len(alerts) == 0

    def test_alert_for_expiring_diagnostic(self):
        today = date.today()
        b = _make_building()
        # Expires in 80 days
        inspection_date = today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS - 80)
        d = _make_diagnostic(b.id, date_inspection=inspection_date)
        alerts = _detect_expiring_diagnostics(b, [d], today)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "diagnostic_expiring"
        assert alerts[0]["severity"] == "warning"
        assert alerts[0]["days_remaining"] == 80

    def test_critical_for_almost_expired(self):
        today = date.today()
        b = _make_building()
        inspection_date = today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS - 15)
        d = _make_diagnostic(b.id, date_inspection=inspection_date)
        alerts = _detect_expiring_diagnostics(b, [d], today)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "critical"

    def test_critical_for_already_expired(self):
        today = date.today()
        b = _make_building()
        inspection_date = today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS + 30)
        d = _make_diagnostic(b.id, date_inspection=inspection_date)
        alerts = _detect_expiring_diagnostics(b, [d], today)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "critical"
        assert alerts[0]["days_remaining"] < 0


class TestDetectInterventionReadinessGaps:
    def test_no_alert_when_no_planned_interventions(self):
        b = _make_building()
        alerts = _detect_intervention_readiness_gaps(b, [], [], date.today())
        assert len(alerts) == 0

    def test_alert_when_planned_without_valid_diagnostic(self):
        today = date.today()
        b = _make_building()
        i = _make_intervention(b.id, date_start=today + timedelta(days=60))
        alerts = _detect_intervention_readiness_gaps(b, [], [i], today)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "intervention_unready"

    def test_no_alert_when_valid_diagnostic_exists(self):
        today = date.today()
        b = _make_building()
        d = _make_diagnostic(b.id, date_inspection=today - timedelta(days=30))
        i = _make_intervention(b.id, date_start=today + timedelta(days=60))
        alerts = _detect_intervention_readiness_gaps(b, [d], [i], today)
        assert len(alerts) == 0


class TestDetectObligationDeadlines:
    def test_alert_for_upcoming_obligation(self):
        today = date.today()
        b = _make_building()
        o = _make_obligation(b.id, due_date=today + timedelta(days=45))
        alerts = _detect_obligation_deadlines(b, [o], today)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "obligation_due"
        assert alerts[0]["severity"] == "warning"

    def test_no_alert_for_completed_obligation(self):
        today = date.today()
        b = _make_building()
        o = _make_obligation(b.id, due_date=today + timedelta(days=10), status="completed")
        alerts = _detect_obligation_deadlines(b, [o], today)
        assert len(alerts) == 0


class TestDetectReadinessDegradation:
    def test_alert_when_readiness_will_degrade(self):
        today = date.today()
        b = _make_building()
        # Diagnostic expires in 60 days -> 90d projection degrades
        inspection_date = today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS - 60)
        d = _make_diagnostic(b.id, date_inspection=inspection_date)
        alerts = _detect_readiness_degradation(b, [d], today)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "readiness_degradation"

    def test_no_alert_when_stable(self):
        today = date.today()
        b = _make_building()
        d = _make_diagnostic(b.id, date_inspection=today - timedelta(days=100))
        alerts = _detect_readiness_degradation(b, [d], today)
        assert len(alerts) == 0


# ── Integration tests with DB ─────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_building_empty(db_session, admin_user):
    """scan_building returns empty result for non-existent building."""
    result = await scan_building(db_session, uuid.uuid4())
    assert result["alerts"] == []
    assert result["summary"]["critical"] == 0


@pytest.mark.asyncio
async def test_scan_building_with_expiring_diagnostic(db_session, admin_user):
    """scan_building detects expiring diagnostics."""
    today = datetime.now(UTC).date()
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.flush()

    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS - 45),
    )
    db_session.add(d)
    await db_session.flush()

    result = await scan_building(db_session, b.id)
    assert len(result["alerts"]) >= 1
    diag_alerts = [a for a in result["alerts"] if a["alert_type"] == "diagnostic_expiring"]
    assert len(diag_alerts) >= 1
    assert diag_alerts[0]["days_remaining"] == 45


@pytest.mark.asyncio
async def test_scan_portfolio_empty_org(db_session, admin_user):
    """scan_portfolio returns empty for org with no buildings."""
    result = await scan_portfolio(db_session, uuid.uuid4())
    assert result["alerts"] == []
    assert result["summary"]["buildings_at_risk"] == 0


@pytest.mark.asyncio
async def test_scan_portfolio_with_buildings(db_session, admin_user):
    """scan_portfolio scans all org buildings."""
    today = datetime.now(UTC).date()
    org_id = admin_user.organization_id or uuid.uuid4()

    b = Building(
        id=uuid.uuid4(),
        address="Rue Portfolio 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        organization_id=org_id,
    )
    db_session.add(b)
    await db_session.flush()

    # Expired diagnostic
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=today - timedelta(days=DIAGNOSTIC_VALIDITY_DAYS + 30),
    )
    db_session.add(d)
    await db_session.flush()

    result = await scan_portfolio(db_session, org_id)
    assert result["summary"]["buildings_at_risk"] >= 1
    assert len(result["projections"]) >= 1
