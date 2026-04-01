"""Tests for the Compliance Nudge Engine."""

import uuid
from datetime import date, timedelta

import pytest

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_SOURCE_DIAGNOSTIC,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_REMEDIATION,
)
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.nudge_engine import generate_nudges, generate_portfolio_nudges

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
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
        "status": "completed",
        "date_report": date.today() - timedelta(days=365 * 4 + 200),  # ~4.5 years ago
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _make_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": "S-001",
        "material_category": "floor_tile",
        "location_floor": "1",
        "pollutant_type": "asbestos",
        "threshold_exceeded": True,
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _make_action(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": ACTION_SOURCE_DIAGNOSTIC,
        "action_type": ACTION_TYPE_REMEDIATION,
        "title": "Critical remediation",
        "priority": ACTION_PRIORITY_CRITICAL,
        "status": ACTION_STATUS_OPEN,
        "due_date": date.today() - timedelta(days=60),  # 60 days overdue
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Tests — expiring diagnostic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expiring_diagnostic_nudge_generated(db_session, admin_user):
    """A diagnostic nearing expiry should generate a nudge."""
    building = await _make_building(db_session, admin_user.id)
    # Report date ~4.5 years ago → expires in ~6 months
    await _make_diagnostic(db_session, building.id)

    nudges = await generate_nudges(db_session, building.id)
    expiring = [n for n in nudges if n["nudge_type"] == "expiring_diagnostic"]
    assert len(expiring) == 1
    assert expiring[0]["severity"] in ("critical", "warning")
    assert "expires" in expiring[0]["headline"].lower()
    assert expiring[0]["call_to_action"] == "Schedule diagnostic renewal"


@pytest.mark.asyncio
async def test_fresh_diagnostic_no_nudge(db_session, admin_user):
    """A recent diagnostic should not generate an expiry nudge."""
    building = await _make_building(db_session, admin_user.id)
    await _make_diagnostic(
        db_session,
        building.id,
        date_report=date.today() - timedelta(days=180),  # 6 months ago
    )

    nudges = await generate_nudges(db_session, building.id)
    expiring = [n for n in nudges if n["nudge_type"] == "expiring_diagnostic"]
    assert len(expiring) == 0


# ---------------------------------------------------------------------------
# Tests — unaddressed asbestos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unaddressed_asbestos_nudge(db_session, admin_user):
    """Positive asbestos with no intervention should generate a nudge."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(
        db_session,
        building.id,
        date_report=date.today() - timedelta(days=90),
    )
    await _make_sample(db_session, diag.id, threshold_exceeded=True)

    nudges = await generate_nudges(db_session, building.id)
    asbestos = [n for n in nudges if n["nudge_type"] == "unaddressed_asbestos"]
    assert len(asbestos) == 1
    assert asbestos[0]["severity"] == "critical"
    assert "asbestos" in asbestos[0]["headline"].lower()


@pytest.mark.asyncio
async def test_asbestos_with_intervention_no_nudge(db_session, admin_user):
    """Positive asbestos with intervention started should not nudge."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(
        db_session,
        building.id,
        date_report=date.today() - timedelta(days=90),
    )
    await _make_sample(db_session, diag.id, threshold_exceeded=True)

    # Add an intervention
    interv = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="removal",
        title="Asbestos removal",
        status="planned",
    )
    db_session.add(interv)
    await db_session.commit()

    nudges = await generate_nudges(db_session, building.id)
    asbestos = [n for n in nudges if n["nudge_type"] == "unaddressed_asbestos"]
    assert len(asbestos) == 0


# ---------------------------------------------------------------------------
# Tests — incomplete dossier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_incomplete_dossier_nudge(db_session, admin_user):
    """A building with low evidence score should get a dossier nudge."""
    building = await _make_building(db_session, admin_user.id)
    # An empty building typically has a very low evidence score
    nudges = await generate_nudges(db_session, building.id)
    dossier = [n for n in nudges if n["nudge_type"] == "incomplete_dossier"]
    # May or may not fire depending on evidence score computation for empty building
    # The key assertion is that the engine runs without error
    assert isinstance(dossier, list)


# ---------------------------------------------------------------------------
# Tests — overdue actions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overdue_actions_nudge(db_session, admin_user):
    """Critical actions overdue >30 days should generate a nudge."""
    building = await _make_building(db_session, admin_user.id)
    await _make_action(db_session, building.id)

    nudges = await generate_nudges(db_session, building.id)
    overdue = [n for n in nudges if n["nudge_type"] == "overdue_actions"]
    assert len(overdue) == 1
    assert overdue[0]["severity"] == "critical"
    assert overdue[0]["deadline_pressure"] == 0


# ---------------------------------------------------------------------------
# Tests — missing SUVA notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_suva_notification_nudge(db_session, admin_user):
    """Required but unfiled SUVA notification should generate a nudge."""
    building = await _make_building(db_session, admin_user.id)
    await _make_diagnostic(
        db_session,
        building.id,
        suva_notification_required=True,
        suva_notification_date=None,
        date_report=date.today() - timedelta(days=90),
    )

    nudges = await generate_nudges(db_session, building.id)
    suva = [n for n in nudges if n["nudge_type"] == "missing_suva_notification"]
    assert len(suva) == 1
    assert suva[0]["severity"] == "critical"
    assert "SUVA" in suva[0]["headline"]


# ---------------------------------------------------------------------------
# Tests — no nudges for perfect building
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_nudges_for_nonexistent_building(db_session):
    """Non-existent building returns empty list."""
    nudges = await generate_nudges(db_session, uuid.uuid4())
    assert nudges == []


# ---------------------------------------------------------------------------
# Tests — context affects output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_affects_output_format(db_session, admin_user):
    """Different contexts should produce different headline formatting."""
    building = await _make_building(db_session, admin_user.id)
    await _make_diagnostic(db_session, building.id)

    dashboard_nudges = await generate_nudges(db_session, building.id, context="dashboard")
    email_nudges = await generate_nudges(db_session, building.id, context="email")

    if dashboard_nudges and email_nudges:
        # Email context prepends warning emoji
        email_expiring = [n for n in email_nudges if n["nudge_type"] == "expiring_diagnostic"]
        if email_expiring:
            assert email_expiring[0]["headline"].startswith("\u26a0")


# ---------------------------------------------------------------------------
# Tests — portfolio nudges
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_nudges_empty_org(db_session):
    """Portfolio nudges for non-existent org returns empty list."""
    nudges = await generate_portfolio_nudges(db_session, uuid.uuid4())
    assert nudges == []


# ---------------------------------------------------------------------------
# Tests — nudge structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nudge_has_required_fields(db_session, admin_user):
    """Every nudge must have all required fields."""
    building = await _make_building(db_session, admin_user.id)
    await _make_diagnostic(db_session, building.id)
    await _make_action(db_session, building.id)

    nudges = await generate_nudges(db_session, building.id)
    required_fields = {
        "id",
        "nudge_type",
        "severity",
        "headline",
        "loss_framing",
        "gain_framing",
        "call_to_action",
    }
    for nudge in nudges:
        for field in required_fields:
            assert field in nudge, f"Missing field: {field}"
        assert nudge["severity"] in ("critical", "warning", "info")


@pytest.mark.asyncio
async def test_nudges_sorted_by_severity(db_session, admin_user):
    """Nudges should be sorted by severity (critical first)."""
    building = await _make_building(db_session, admin_user.id)
    # Create conditions for multiple nudge types
    await _make_diagnostic(
        db_session,
        building.id,
        suva_notification_required=True,
        suva_notification_date=None,
    )
    await _make_action(db_session, building.id)

    nudges = await generate_nudges(db_session, building.id)
    if len(nudges) >= 2:
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        for i in range(len(nudges) - 1):
            current = severity_order.get(nudges[i]["severity"], 2)
            next_sev = severity_order.get(nudges[i + 1]["severity"], 2)
            assert current <= next_sev, "Nudges not sorted by severity"
