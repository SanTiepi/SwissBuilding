"""Tests for the Compliance Timeline service and endpoints."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.compliance_timeline_service import (
    analyze_compliance_gaps,
    build_compliance_timeline,
    get_compliance_deadlines,
    get_compliance_periods,
    get_next_compliance_actions,
    get_pollutant_compliance_states,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    return Building(**defaults)


def _make_diagnostic(building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "full",
        "status": "completed",
        "date_report": date.today(),
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return Diagnostic(**defaults)


def _make_sample(diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": "S001",
        "pollutant_type": "asbestos",
        "concentration": 0.05,
        "unit": "percent_weight",
        "threshold_exceeded": False,
        "risk_level": "low",
    }
    defaults.update(kwargs)
    return Sample(**defaults)


def _make_intervention(building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "asbestos_removal",
        "title": "Asbestos removal",
        "status": "completed",
        "date_end": date.today(),
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return Intervention(**defaults)


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_no_diagnostics(db_session, admin_user):
    """Timeline for building with no diagnostics returns non_compliant (missing diagnostics)."""
    building = _make_building(admin_user)
    db_session.add(building)
    await db_session.commit()

    result = await build_compliance_timeline(db_session, building.id)
    assert result.building_id == building.id
    # Building from 1965 has relevant pollutants requiring diagnostics
    assert result.current_status == "non_compliant"
    # No diagnostic events, but gap events may exist
    diag_events = [e for e in result.events if e.event_type == "diagnostic_completed"]
    assert diag_events == []


@pytest.mark.asyncio
async def test_timeline_nonexistent_building(db_session):
    """Timeline for nonexistent building returns empty unknown timeline."""
    result = await build_compliance_timeline(db_session, uuid.uuid4())
    assert result.current_status == "unknown"
    assert result.events == []


@pytest.mark.asyncio
async def test_timeline_with_completed_diagnostic(db_session, admin_user):
    """Completed diagnostic generates an event in the timeline."""
    building = _make_building(admin_user)
    db_session.add(building)
    await db_session.flush()

    diag = _make_diagnostic(building.id, date_report=date.today())
    sample = _make_sample(diag.id, pollutant_type="asbestos", concentration=0.01, risk_level="low")
    db_session.add_all([diag, sample])
    await db_session.commit()

    result = await build_compliance_timeline(db_session, building.id)
    diag_events = [e for e in result.events if e.event_type == "diagnostic_completed"]
    assert len(diag_events) >= 1
    assert "full" in diag_events[0].title.lower()


@pytest.mark.asyncio
async def test_timeline_with_completed_intervention(db_session, admin_user):
    """Completed intervention generates an event in the timeline."""
    building = _make_building(admin_user)
    db_session.add(building)
    await db_session.flush()

    intv = _make_intervention(building.id, date_end=date.today())
    db_session.add(intv)
    await db_session.commit()

    result = await build_compliance_timeline(db_session, building.id)
    intv_events = [e for e in result.events if e.event_type == "intervention_done"]
    assert len(intv_events) == 1


@pytest.mark.asyncio
async def test_deadlines_overdue_asbestos(db_session, admin_user):
    """Pre-1991 building with old diagnostic has overdue asbestos deadline."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.flush()

    old_date = date.today() - timedelta(days=4 * 365)
    diag = _make_diagnostic(building.id, date_report=old_date)
    sample = _make_sample(diag.id, pollutant_type="asbestos")
    db_session.add_all([diag, sample])
    await db_session.commit()

    deadlines = await get_compliance_deadlines(db_session, building.id)
    asbestos_deadlines = [d for d in deadlines if "asbestos" in d.description.lower()]
    assert len(asbestos_deadlines) >= 1
    assert asbestos_deadlines[0].status == "overdue"


@pytest.mark.asyncio
async def test_deadlines_upcoming_pcb(db_session, admin_user):
    """Building 1955-1975 with recent PCB diagnostic has upcoming/met PCB deadline."""
    building = _make_building(admin_user, construction_year=1960)
    db_session.add(building)
    await db_session.flush()

    # PCB diagnostic done 4.5 years ago — renewal is 5 years, so upcoming (within 90 days? No, 6 months left)
    recent_date = date.today() - timedelta(days=int(4.8 * 365))
    diag = _make_diagnostic(building.id, diagnostic_type="pcb", date_report=recent_date)
    sample = _make_sample(diag.id, pollutant_type="pcb", concentration=10.0, unit="mg_per_kg")
    db_session.add_all([diag, sample])
    await db_session.commit()

    deadlines = await get_compliance_deadlines(db_session, building.id)
    pcb_deadlines = [d for d in deadlines if "pcb" in d.description.lower()]
    assert len(pcb_deadlines) == 1
    # 4.8 years old, renewal is 5 years -> ~73 days remaining -> upcoming
    assert pcb_deadlines[0].status == "upcoming"


@pytest.mark.asyncio
async def test_pollutant_states_compliant(db_session, admin_user):
    """Building with recent clean diagnostics is compliant."""
    building = _make_building(admin_user, construction_year=1965)
    db_session.add(building)
    await db_session.flush()

    diag = _make_diagnostic(building.id, date_report=date.today())
    samples = [
        _make_sample(diag.id, pollutant_type="asbestos", concentration=0.01, risk_level="low"),
        _make_sample(diag.id, pollutant_type="pcb", concentration=5.0, unit="mg_per_kg", risk_level="low"),
        _make_sample(diag.id, pollutant_type="lead", concentration=100.0, unit="mg_per_kg", risk_level="low"),
        _make_sample(diag.id, pollutant_type="hap", concentration=10.0, unit="mg_per_kg", risk_level="low"),
        _make_sample(diag.id, pollutant_type="radon", concentration=50.0, unit="bq_per_m3", risk_level="low"),
    ]
    db_session.add(diag)
    db_session.add_all(samples)
    await db_session.commit()

    states = await get_pollutant_compliance_states(db_session, building.id)
    asbestos_state = next(s for s in states if s.pollutant == "asbestos")
    assert asbestos_state.compliant is True
    assert asbestos_state.requires_action is False


@pytest.mark.asyncio
async def test_pollutant_states_expired_diagnostic(db_session, admin_user):
    """Expired asbestos diagnostic makes pollutant non-compliant."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.flush()

    old_date = date.today() - timedelta(days=4 * 365)
    diag = _make_diagnostic(building.id, date_report=old_date)
    sample = _make_sample(diag.id, pollutant_type="asbestos", concentration=0.01, risk_level="low")
    db_session.add_all([diag, sample])
    await db_session.commit()

    states = await get_pollutant_compliance_states(db_session, building.id)
    asbestos_state = next(s for s in states if s.pollutant == "asbestos")
    assert asbestos_state.compliant is False
    assert asbestos_state.requires_action is True
    assert "expired" in asbestos_state.detail.lower()


@pytest.mark.asyncio
async def test_pollutant_states_active_intervention(db_session, admin_user):
    """Active intervention is detected in pollutant state."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.flush()

    diag = _make_diagnostic(building.id, date_report=date.today())
    sample = _make_sample(
        diag.id,
        pollutant_type="asbestos",
        concentration=5.0,
        risk_level="critical",
        threshold_exceeded=True,
    )
    intv = _make_intervention(
        building.id,
        intervention_type="asbestos_removal",
        status="in_progress",
    )
    db_session.add_all([diag, sample, intv])
    await db_session.commit()

    states = await get_pollutant_compliance_states(db_session, building.id)
    asbestos_state = next(s for s in states if s.pollutant == "asbestos")
    assert asbestos_state.has_active_intervention is True


@pytest.mark.asyncio
async def test_gap_analysis_missing_diagnostic(db_session, admin_user):
    """Building with no diagnostics has missing diagnostic gaps."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.commit()

    analysis = await analyze_compliance_gaps(db_session, building.id)
    assert analysis.total_gaps > 0
    gap_types = [g["gap_type"] for g in analysis.gaps]
    assert "missing_diagnostic" in gap_types


@pytest.mark.asyncio
async def test_gap_analysis_expired_diagnostic(db_session, admin_user):
    """Expired diagnostic shows up in gap analysis."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.flush()

    old_date = date.today() - timedelta(days=4 * 365)
    diag = _make_diagnostic(building.id, date_report=old_date)
    sample = _make_sample(diag.id, pollutant_type="asbestos", concentration=0.01, risk_level="low")
    db_session.add_all([diag, sample])
    await db_session.commit()

    analysis = await analyze_compliance_gaps(db_session, building.id)
    expired = [g for g in analysis.gaps if g["gap_type"] == "expired_diagnostic"]
    assert len(expired) >= 1
    assert expired[0]["pollutant"] == "asbestos"


@pytest.mark.asyncio
async def test_gap_analysis_untreated_high_risk(db_session, admin_user):
    """High-risk sample without intervention shows as gap."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.flush()

    diag = _make_diagnostic(building.id, date_report=date.today())
    sample = _make_sample(
        diag.id,
        pollutant_type="asbestos",
        concentration=5.0,
        risk_level="critical",
        threshold_exceeded=True,
    )
    db_session.add_all([diag, sample])
    await db_session.commit()

    analysis = await analyze_compliance_gaps(db_session, building.id)
    high_risk = [g for g in analysis.gaps if g["gap_type"] == "untreated_high_risk"]
    assert len(high_risk) >= 1
    assert analysis.critical_gaps >= 1


@pytest.mark.asyncio
async def test_compliance_periods_reconstruction(db_session, admin_user):
    """Compliance periods are reconstructed from diagnostic history."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.flush()

    # First diagnostic: clean
    d1 = date.today() - timedelta(days=365)
    diag1 = _make_diagnostic(building.id, date_report=d1, diagnostic_type="full")
    sample1 = _make_sample(diag1.id, pollutant_type="asbestos", concentration=0.01, risk_level="low")

    # Second diagnostic: high risk
    d2 = date.today() - timedelta(days=180)
    diag2 = _make_diagnostic(building.id, date_report=d2, diagnostic_type="asbestos")
    sample2 = _make_sample(
        diag2.id,
        pollutant_type="asbestos",
        concentration=5.0,
        risk_level="critical",
        threshold_exceeded=True,
    )

    db_session.add_all([diag1, sample1, diag2, sample2])
    await db_session.commit()

    periods = await get_compliance_periods(db_session, building.id)
    assert len(periods) >= 2
    statuses = [p.status for p in periods]
    assert "compliant" in statuses
    assert "non_compliant" in statuses


@pytest.mark.asyncio
async def test_next_actions_prioritization(db_session, admin_user):
    """Next actions are returned in priority order."""
    building = _make_building(admin_user, construction_year=1970)
    db_session.add(building)
    await db_session.flush()

    # Old diagnostic (expired) with high-risk sample
    old_date = date.today() - timedelta(days=4 * 365)
    diag = _make_diagnostic(building.id, date_report=old_date)
    sample = _make_sample(
        diag.id,
        pollutant_type="asbestos",
        concentration=5.0,
        risk_level="critical",
        threshold_exceeded=True,
    )
    db_session.add_all([diag, sample])
    await db_session.commit()

    actions = await get_next_compliance_actions(db_session, building.id)
    assert len(actions) >= 1
    # Overdue deadlines should be priority 1
    priorities = [a["priority"] for a in actions]
    assert priorities == sorted(priorities)


@pytest.mark.asyncio
async def test_multiple_pollutants_mixed_compliance(db_session, admin_user):
    """Building with mixed pollutant compliance states."""
    building = _make_building(admin_user, construction_year=1965)
    db_session.add(building)
    await db_session.flush()

    diag = _make_diagnostic(building.id, date_report=date.today())
    # Asbestos: high risk
    s1 = _make_sample(
        diag.id,
        pollutant_type="asbestos",
        concentration=5.0,
        risk_level="critical",
        threshold_exceeded=True,
    )
    # PCB: clean
    s2 = _make_sample(
        diag.id,
        pollutant_type="pcb",
        concentration=5.0,
        unit="mg_per_kg",
        risk_level="low",
    )
    # Lead: clean
    s3 = _make_sample(
        diag.id,
        pollutant_type="lead",
        concentration=100.0,
        unit="mg_per_kg",
        risk_level="low",
    )
    db_session.add_all([diag, s1, s2, s3])
    await db_session.commit()

    states = await get_pollutant_compliance_states(db_session, building.id)
    asbestos = next(s for s in states if s.pollutant == "asbestos")
    pcb = next(s for s in states if s.pollutant == "pcb")
    assert asbestos.compliant is False
    assert pcb.compliant is True


@pytest.mark.asyncio
async def test_post_1991_no_asbestos_concern(db_session, admin_user):
    """Post-1991 building does not require asbestos diagnostic."""
    building = _make_building(admin_user, construction_year=2000)
    db_session.add(building)
    await db_session.commit()

    states = await get_pollutant_compliance_states(db_session, building.id)
    asbestos = next(s for s in states if s.pollutant == "asbestos")
    assert asbestos.compliant is True
    assert "not relevant" in asbestos.detail.lower()


@pytest.mark.asyncio
async def test_current_status_compliant(db_session, admin_user):
    """Timeline current_status is compliant when all pollutants are compliant."""
    building = _make_building(admin_user, construction_year=2000)
    db_session.add(building)
    await db_session.flush()

    diag = _make_diagnostic(building.id, date_report=date.today())
    samples = [
        _make_sample(diag.id, pollutant_type="lead", concentration=100.0, unit="mg_per_kg", risk_level="low"),
        _make_sample(diag.id, pollutant_type="hap", concentration=10.0, unit="mg_per_kg", risk_level="low"),
        _make_sample(diag.id, pollutant_type="radon", concentration=50.0, unit="bq_per_m3", risk_level="low"),
    ]
    db_session.add(diag)
    db_session.add_all(samples)
    await db_session.commit()

    result = await build_compliance_timeline(db_session, building.id)
    assert result.current_status == "compliant"


@pytest.mark.asyncio
async def test_gap_analysis_nonexistent_building(db_session):
    """Gap analysis for nonexistent building returns empty result."""
    analysis = await analyze_compliance_gaps(db_session, uuid.uuid4())
    assert analysis.total_gaps == 0
    assert analysis.gaps == []


@pytest.mark.asyncio
async def test_compliance_periods_no_diagnostics(db_session, admin_user):
    """Building with no diagnostics returns unknown period."""
    building = _make_building(admin_user)
    db_session.add(building)
    await db_session.commit()

    periods = await get_compliance_periods(db_session, building.id)
    assert len(periods) == 1
    assert periods[0].status == "unknown"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_timeline_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/compliance/timeline returns valid response."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "building_id" in data
    assert "events" in data
    assert "current_status" in data


@pytest.mark.asyncio
async def test_api_deadlines_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/compliance/deadlines returns list."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance/deadlines",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_pollutant_states_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/compliance/pollutant-states returns list."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance/pollutant-states",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 6  # 6 pollutants (including pfas)


@pytest.mark.asyncio
async def test_api_gap_analysis_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/compliance/gap-analysis returns analysis."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance/gap-analysis",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "building_id" in data
    assert "total_gaps" in data


@pytest.mark.asyncio
async def test_api_next_actions_endpoint(client, auth_headers, sample_building):
    """GET /buildings/{id}/compliance/next-actions returns list."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/compliance/next-actions",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_timeline_404(client, auth_headers):
    """Non-existent building returns 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/compliance/timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 404
