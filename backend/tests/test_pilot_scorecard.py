"""Tests for the G2 Pilot Scorecard service and API endpoints.

Covers:
  - Scorecard with 0 buildings (empty org)
  - Scorecard with mixed readiness states
  - Building scorecard structure
  - Weekly summary structure
  - Trend detection (improving / stable / degrading)
  - Pilot health classification (on_track / at_risk / behind)
  - API endpoint contracts
  - Prospect seed scenario integration
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_pack import EvidencePack
from app.models.organization import Organization
from app.services.pilot_scorecard_service import (
    _compute_pilot_health,
    _compute_trend,
    _is_diagnostic_valid,
    get_building_scorecard,
    get_pilot_scorecard,
    get_weekly_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(db_session) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Pilot Org",
        type="property_management",
    )
    db_session.add(org)
    return org


def _make_building(db_session, admin_user, org, **kwargs):
    defaults = {
        "address": "Rue de Test 1",
        "postal_code": "1003",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "status": "active",
    }
    defaults.update(kwargs)
    building = Building(
        id=uuid.uuid4(),
        created_by=admin_user.id,
        organization_id=org.id,
        **defaults,
    )
    db_session.add(building)
    return building


def _make_diagnostic(db_session, building, *, diag_type="asbestos", status="completed", report_date=None, **kwargs):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type=diag_type,
        diagnostic_context="AvT",
        status=status,
        date_inspection=date(2024, 1, 15),
        date_report=report_date or date(2024, 1, 30),
        **kwargs,
    )
    db_session.add(diag)
    return diag


def _make_document(db_session, building, **kwargs):
    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path="/docs/test/report.pdf",
        file_name="report.pdf",
        document_type="diagnostic_report",
        **kwargs,
    )
    db_session.add(doc)
    return doc


def _make_action(db_session, building, *, priority="medium", status="open", **kwargs):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="notification",
        title="Test action",
        priority=priority,
        status=status,
        **kwargs,
    )
    db_session.add(action)
    return action


def _make_pack(db_session, building, *, status="draft", submitted_at=None, notes=None, **kwargs):
    pack = EvidencePack(
        id=uuid.uuid4(),
        building_id=building.id,
        pack_type="authority_pack",
        title="Test pack",
        status=status,
        submitted_at=submitted_at,
        notes=notes,
        **kwargs,
    )
    db_session.add(pack)
    return pack


# ---------------------------------------------------------------------------
# Unit tests for pure helpers
# ---------------------------------------------------------------------------


class TestDiagnosticValidity:
    def test_valid_recent(self):
        assert _is_diagnostic_valid(date(2024, 6, 1)) is True

    def test_expired_old(self):
        old = date(2020, 1, 1)
        assert _is_diagnostic_valid(old) is False

    def test_none_date(self):
        assert _is_diagnostic_valid(None) is False

    def test_exact_boundary(self):
        today = datetime.now(UTC).date()
        boundary = today - timedelta(days=3 * 365)
        assert _is_diagnostic_valid(boundary) is True

    def test_just_expired(self):
        today = datetime.now(UTC).date()
        expired = today - timedelta(days=3 * 365 + 1)
        assert _is_diagnostic_valid(expired) is False


class TestTrendComputation:
    def test_improving(self):
        assert _compute_trend(10, 3) == "improving"

    def test_degrading(self):
        assert _compute_trend(1, 8) == "degrading"

    def test_stable(self):
        assert _compute_trend(5, 5) == "stable"

    def test_borderline_improving(self):
        assert _compute_trend(5, 3) == "stable"  # net = 2, threshold is > 2


class TestPilotHealth:
    def test_on_track(self):
        assert _compute_pilot_health(60, 50, 2, 5) == "on_track"

    def test_behind(self):
        assert _compute_pilot_health(10, 10, 0, 5) == "behind"

    def test_at_risk(self):
        assert _compute_pilot_health(30, 30, 0, 5) == "at_risk"

    def test_empty(self):
        assert _compute_pilot_health(0, 0, 0, 0) == "on_track"


# ---------------------------------------------------------------------------
# Integration tests with DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scorecard_empty_org(db_session, admin_user):
    """Scorecard with 0 buildings returns empty structure."""
    org = _make_org(db_session)
    await db_session.flush()

    result = await get_pilot_scorecard(db_session, org.id)

    assert result["org_id"] == str(org.id)
    assert result["buildings"]["total"] == 0
    assert result["trend"] == "stable"
    assert result["pilot_health"] == "on_track"
    assert result["actions"]["total_created"] == 0
    assert result["diagnostics"]["total"] == 0


@pytest.mark.asyncio
async def test_scorecard_mixed_readiness(db_session, admin_user):
    """Scorecard with mixed building readiness states."""
    org = _make_org(db_session)

    # Building 1: ready (valid diagnostic + document + no blockers)
    b1 = _make_building(db_session, admin_user, org, address="B1 Ready")
    _make_diagnostic(db_session, b1, report_date=date(2024, 6, 1))
    _make_document(db_session, b1)
    _make_action(db_session, b1, status="done", priority="high", completed_at=datetime(2024, 7, 1, tzinfo=UTC))

    # Building 2: not ready (expired diagnostic + blockers)
    b2 = _make_building(db_session, admin_user, org, address="B2 Not Ready")
    _make_diagnostic(db_session, b2, report_date=date(2020, 1, 1))
    _make_action(db_session, b2, priority="critical", status="open")

    # Building 3: no diagnostics at all
    _make_building(db_session, admin_user, org, address="B3 Empty")

    await db_session.flush()

    result = await get_pilot_scorecard(db_session, org.id)

    assert result["buildings"]["total"] == 3
    assert result["buildings"]["assessed"] == 2  # b1 + b2 have diagnostics
    assert result["diagnostics"]["total"] == 2
    assert result["diagnostics"]["valid"] >= 1
    assert result["diagnostics"]["expired"] >= 1
    assert result["diagnostics"]["missing_coverage"] == 1  # b3
    assert result["readiness"]["buildings_with_blockers"] >= 1


@pytest.mark.asyncio
async def test_building_scorecard_structure(db_session, admin_user):
    """Building scorecard returns correct structure."""
    org = _make_org(db_session)
    b = _make_building(db_session, admin_user, org, address="Rue de Bourg 12")
    _make_diagnostic(db_session, b, report_date=date(2024, 3, 1))
    _make_document(db_session, b)
    _make_action(db_session, b, priority="high", status="open")
    _make_action(db_session, b, priority="medium", status="done", completed_at=datetime(2024, 5, 1, tzinfo=UTC))
    await db_session.flush()

    result = await get_building_scorecard(db_session, b.id)

    assert result["building_id"] == str(b.id)
    assert result["building_name"] == "Rue de Bourg 12"
    assert "completeness_pct" in result
    assert "blockers_open" in result
    assert "actions_total" in result
    assert "dossier_stage" in result
    assert "dossier_stage_label" in result
    assert result["actions_total"] == 2
    assert result["actions_completed"] == 1


@pytest.mark.asyncio
async def test_building_scorecard_not_found(db_session, admin_user):
    """Building scorecard for non-existent building returns error."""
    result = await get_building_scorecard(db_session, uuid.uuid4())
    assert result.get("error") == "building_not_found"


@pytest.mark.asyncio
async def test_building_scorecard_dossier_stage_submitted(db_session, admin_user):
    """Building with submitted pack shows 'submitted' stage."""
    org = _make_org(db_session)
    b = _make_building(db_session, admin_user, org)
    _make_diagnostic(db_session, b, report_date=date(2024, 3, 1))
    _make_pack(db_session, b, status="submitted", submitted_at=datetime(2024, 5, 1, tzinfo=UTC))
    await db_session.flush()

    result = await get_building_scorecard(db_session, b.id)
    assert result["dossier_stage"] == "submitted"


@pytest.mark.asyncio
async def test_building_scorecard_complement_requested(db_session, admin_user):
    """Building with complement_requested pack shows correct stage."""
    org = _make_org(db_session)
    b = _make_building(db_session, admin_user, org)
    _make_diagnostic(db_session, b, report_date=date(2024, 3, 1))
    _make_pack(
        db_session,
        b,
        status="submitted",
        submitted_at=datetime(2024, 5, 1, tzinfo=UTC),
        notes='{"complement_requested": true, "complement_details": "Need PCB"}',
    )
    await db_session.flush()

    result = await get_building_scorecard(db_session, b.id)
    assert result["dossier_stage"] == "complement_requested"


@pytest.mark.asyncio
async def test_weekly_summary_structure(db_session, admin_user):
    """Weekly summary returns correct structure."""
    org = _make_org(db_session)
    b = _make_building(db_session, admin_user, org)
    _make_action(db_session, b, status="done", completed_at=datetime.now(UTC) - timedelta(days=2))
    _make_action(db_session, b, status="open")
    await db_session.flush()

    result = await get_weekly_summary(db_session, org.id)

    assert result["org_id"] == str(org.id)
    assert "period" in result
    assert "completed_this_week" in result
    assert "created_this_week" in result
    assert "due_next_week" in result
    assert "open_actions_total" in result
    assert "readiness_trend" in result
    assert "pilot_progress" in result


@pytest.mark.asyncio
async def test_weekly_summary_empty_org(db_session, admin_user):
    """Weekly summary with no buildings returns empty structure."""
    org = _make_org(db_session)
    await db_session.flush()

    result = await get_weekly_summary(db_session, org.id)
    assert result["open_actions_total"] == 0
    assert result["completed_this_week"]["count"] == 0


@pytest.mark.asyncio
async def test_scorecard_with_packs(db_session, admin_user):
    """Scorecard correctly counts packs and dossier metrics."""
    org = _make_org(db_session)
    b1 = _make_building(db_session, admin_user, org, address="B1")
    b2 = _make_building(db_session, admin_user, org, address="B2")

    _make_diagnostic(db_session, b1, report_date=date(2024, 3, 1))
    _make_diagnostic(db_session, b2, report_date=date(2024, 4, 1))

    _make_action(db_session, b1, status="done", completed_at=datetime(2024, 4, 1, tzinfo=UTC))

    _make_pack(db_session, b1, status="submitted", submitted_at=datetime(2024, 5, 1, tzinfo=UTC))
    _make_pack(
        db_session,
        b2,
        status="submitted",
        submitted_at=datetime(2024, 5, 5, tzinfo=UTC),
        notes='{"complement_requested": true}',
    )
    await db_session.flush()

    result = await get_pilot_scorecard(db_session, org.id)

    assert result["dossiers"]["packs_generated"] == 2
    assert result["dossiers"]["packs_submitted"] == 2
    assert result["dossiers"]["complements_received"] == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_pilot_scorecard(client, auth_headers):
    """GET /pilot/scorecard returns 200."""
    response = await client.get(
        "/api/v1/pilot/scorecard",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "buildings" in data or "error" in data


@pytest.mark.asyncio
async def test_api_pilot_scorecard_with_baseline(client, auth_headers):
    """GET /pilot/scorecard?baseline_date=2024-01-01 returns 200."""
    response = await client.get(
        "/api/v1/pilot/scorecard?baseline_date=2024-01-01",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_building_scorecard(client, auth_headers):
    """GET /buildings/{id}/scorecard returns 200 for valid building or error structure."""
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/v1/buildings/{fake_id}/scorecard",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Non-existent building returns error field
    assert data.get("error") == "building_not_found" or "building_id" in data


@pytest.mark.asyncio
async def test_api_weekly_summary(client, auth_headers):
    """GET /pilot/weekly-summary returns 200."""
    response = await client.get(
        "/api/v1/pilot/weekly-summary",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "pilot_progress" in data or "error" in data
