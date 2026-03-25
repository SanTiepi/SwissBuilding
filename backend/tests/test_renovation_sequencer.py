"""Tests for the Renovation Sequencer service and API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.services.renovation_sequencer_service import (
    estimate_renovation_timeline,
    get_renovation_readiness_blockers,
    identify_parallel_tracks,
    plan_renovation_sequence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH = "$2b$12$LJ3m4ys3Lg7E16eDLBBCVuVGkMBj6bneeMjkVDO7ZPMDhMLsBXKje"  # 'test'


def _make_user(db_session, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH,
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
    )
    defaults.update(kw)
    user = User(**defaults)
    db_session.add(user)
    return user


def _make_building(db_session, user_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user_id,
        status="active",
    )
    defaults.update(kw)
    b = Building(**defaults)
    db_session.add(b)
    return b


def _make_diagnostic(db_session, building_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="completed",
    )
    defaults.update(kw)
    d = Diagnostic(**defaults)
    db_session.add(d)
    return d


def _make_sample(db_session, diagnostic_id, **kw):
    defaults = dict(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:4]}",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
        location_floor="1st floor",
    )
    defaults.update(kw)
    s = Sample(**defaults)
    db_session.add(s)
    return s


def _auth_headers(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# FN1: plan_renovation_sequence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequence_empty_building(db_session):
    """Building with no samples produces structural + finishing phases only."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    result = await plan_renovation_sequence(db_session, building.id)
    assert result.building_id == building.id
    # Should have structural + finishing at minimum
    assert result.total_phases >= 2
    assert any("structural" in p.title.lower() for p in result.phases)


@pytest.mark.asyncio
async def test_sequence_nonexistent_building(db_session):
    """Nonexistent building returns empty sequence."""
    result = await plan_renovation_sequence(db_session, uuid.uuid4())
    assert result.total_phases == 0
    assert result.phases == []


@pytest.mark.asyncio
async def test_sequence_asbestos_first(db_session):
    """Asbestos remediation comes before other pollutants."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag_a = _make_diagnostic(db_session, building.id, diagnostic_type="asbestos")
    diag_p = _make_diagnostic(db_session, building.id, diagnostic_type="pcb")
    _make_sample(db_session, diag_a.id, pollutant_type="asbestos")
    _make_sample(db_session, diag_p.id, pollutant_type="pcb")
    await db_session.commit()

    result = await plan_renovation_sequence(db_session, building.id)
    remediation_phases = [p for p in result.phases if p.pollutant]
    assert len(remediation_phases) >= 2
    assert remediation_phases[0].pollutant == "asbestos"
    assert remediation_phases[1].pollutant == "pcb"


@pytest.mark.asyncio
async def test_sequence_lab_phase_included(db_session):
    """Lab analysis phase is added when pollutants are found."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(db_session, diag.id)
    await db_session.commit()

    result = await plan_renovation_sequence(db_session, building.id)
    assert any("lab" in p.title.lower() for p in result.phases)
    # Lab phase should be order 0
    lab = next(p for p in result.phases if "lab" in p.title.lower())
    assert lab.order == 0


@pytest.mark.asyncio
async def test_sequence_dependencies_present(db_session):
    """Dependencies are generated between phases."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(db_session, diag.id)
    await db_session.commit()

    result = await plan_renovation_sequence(db_session, building.id)
    assert len(result.dependencies) > 0


@pytest.mark.asyncio
async def test_sequence_structural_after_remediation(db_session):
    """Structural work comes after all pollutant remediation."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(db_session, diag.id, pollutant_type="asbestos")
    await db_session.commit()

    result = await plan_renovation_sequence(db_session, building.id)
    remediation = [p for p in result.phases if p.pollutant]
    structural = [p for p in result.phases if "structural" in p.title.lower()]
    assert structural
    for r in remediation:
        assert r.order < structural[0].order


# ---------------------------------------------------------------------------
# FN2: estimate_renovation_timeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_empty_building(db_session):
    """Empty building produces a timeline with non-zero duration."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    result = await estimate_renovation_timeline(db_session, building.id)
    assert result.building_id == building.id
    assert result.total_duration_weeks > 0


@pytest.mark.asyncio
async def test_timeline_lab_buffer(db_session):
    """Timeline includes lab analysis buffer."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(db_session, diag.id)
    await db_session.commit()

    result = await estimate_renovation_timeline(db_session, building.id)
    assert result.lab_analysis_buffer_weeks == 3


@pytest.mark.asyncio
async def test_timeline_critical_path(db_session):
    """Critical path is populated."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(db_session, diag.id)
    await db_session.commit()

    result = await estimate_renovation_timeline(db_session, building.id)
    assert len(result.critical_path) > 0
    # Critical path phases should be on the Gantt
    all_ids = {p.phase_id for p in result.phases}
    for cp in result.critical_path:
        assert cp in all_ids


@pytest.mark.asyncio
async def test_timeline_phases_have_weeks(db_session):
    """Each Gantt phase has start/end/duration in weeks."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    result = await estimate_renovation_timeline(db_session, building.id)
    for phase in result.phases:
        assert phase.end_week > phase.start_week
        assert phase.duration_weeks == phase.end_week - phase.start_week


@pytest.mark.asyncio
async def test_timeline_nonexistent_building(db_session):
    """Nonexistent building returns zero-duration timeline."""
    result = await estimate_renovation_timeline(db_session, uuid.uuid4())
    assert result.total_duration_weeks == 0


# ---------------------------------------------------------------------------
# FN3: identify_parallel_tracks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_no_pollutants(db_session):
    """Building without pollutants has no parallel tracks."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    result = await identify_parallel_tracks(db_session, building.id)
    assert result.tracks == []
    assert result.sequential_duration_weeks > 0


@pytest.mark.asyncio
async def test_parallel_different_zones(db_session):
    """Different zones with independent pollutants can be parallel."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag_a = _make_diagnostic(db_session, building.id, diagnostic_type="asbestos")
    diag_p = _make_diagnostic(db_session, building.id, diagnostic_type="pcb")
    _make_sample(db_session, diag_a.id, pollutant_type="asbestos", location_floor="1st floor")
    _make_sample(db_session, diag_p.id, pollutant_type="pcb", location_floor="basement")
    await db_session.commit()

    result = await identify_parallel_tracks(db_session, building.id)
    assert len(result.tracks) >= 1
    assert result.total_potential_savings_weeks > 0
    assert result.optimized_duration_weeks < result.sequential_duration_weeks


@pytest.mark.asyncio
async def test_parallel_radon_with_exterior(db_session):
    """Radon + exterior pollutant can run in parallel."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    diag_r = _make_diagnostic(db_session, building.id, diagnostic_type="radon")
    diag_p = _make_diagnostic(db_session, building.id, diagnostic_type="pcb")
    _make_sample(db_session, diag_r.id, pollutant_type="radon", location_floor="basement")
    _make_sample(db_session, diag_p.id, pollutant_type="pcb", location_floor="facade")
    await db_session.commit()

    result = await identify_parallel_tracks(db_session, building.id)
    radon_tracks = [t for t in result.tracks if "radon" in t.reason.lower()]
    assert len(radon_tracks) >= 1


@pytest.mark.asyncio
async def test_parallel_optimized_duration(db_session):
    """Optimized duration is less than or equal to sequential."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id)
    await db_session.commit()

    result = await identify_parallel_tracks(db_session, building.id)
    assert result.optimized_duration_weeks <= result.sequential_duration_weeks


# ---------------------------------------------------------------------------
# FN4: get_renovation_readiness_blockers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blockers_nonexistent_building(db_session):
    """Nonexistent building returns a critical blocker."""
    result = await get_renovation_readiness_blockers(db_session, uuid.uuid4())
    assert result.total_blockers == 1
    assert result.critical_blockers == 1
    assert not result.is_ready


@pytest.mark.asyncio
async def test_blockers_missing_asbestos_diagnostic(db_session):
    """Pre-1991 building without asbestos diagnostic is blocked."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id, construction_year=1970)
    await db_session.commit()

    result = await get_renovation_readiness_blockers(db_session, building.id)
    asbestos_blockers = [b for b in result.blockers if "asbestos" in b.title.lower()]
    assert len(asbestos_blockers) >= 1
    assert not result.is_ready


@pytest.mark.asyncio
async def test_blockers_missing_pcb_diagnostic(db_session):
    """1955-1975 building without PCB diagnostic is blocked."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id, construction_year=1965)
    await db_session.commit()

    result = await get_renovation_readiness_blockers(db_session, building.id)
    pcb_blockers = [b for b in result.blockers if "pcb" in b.title.lower()]
    assert len(pcb_blockers) >= 1


@pytest.mark.asyncio
async def test_blockers_suva_notification_pending(db_session):
    """SUVA notification required but not sent creates a blocker."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id, construction_year=2000)
    _make_diagnostic(
        db_session,
        building.id,
        diagnostic_type="asbestos",
        status="completed",
        suva_notification_required=True,
        suva_notification_date=None,
    )
    await db_session.commit()

    result = await get_renovation_readiness_blockers(db_session, building.id)
    suva_blockers = [b for b in result.blockers if "suva" in b.title.lower()]
    assert len(suva_blockers) >= 1
    assert suva_blockers[0].severity == "critical"


@pytest.mark.asyncio
async def test_blockers_open_critical_actions(db_session):
    """Open high-priority actions create a blocker."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id, construction_year=2000)
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Urgent remediation",
        priority="critical",
        status="open",
    )
    db_session.add(action)
    await db_session.commit()

    result = await get_renovation_readiness_blockers(db_session, building.id)
    compliance_blockers = [b for b in result.blockers if b.category == "compliance_gap"]
    assert len(compliance_blockers) >= 1


@pytest.mark.asyncio
async def test_blockers_no_contractor(db_session):
    """Building without contractor assignment has a blocker."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id, construction_year=2000)
    await db_session.commit()

    result = await get_renovation_readiness_blockers(db_session, building.id)
    contractor_blockers = [b for b in result.blockers if b.category == "missing_contractor"]
    assert len(contractor_blockers) >= 1


@pytest.mark.asyncio
async def test_blockers_ready_building(db_session):
    """Fully ready building (modern, all diagnostics, contractor assigned) has no blockers."""
    user = _make_user(db_session)
    building = _make_building(db_session, user.id, construction_year=2005)
    # Assign a contractor
    assignment = Assignment(
        id=uuid.uuid4(),
        target_type="building",
        target_id=building.id,
        user_id=user.id,
        role="contractor_contact",
        created_by=user.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    result = await get_renovation_readiness_blockers(db_session, building.id)
    assert result.is_ready
    assert result.total_blockers == 0


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_renovation_sequence(client, admin_user, sample_building, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-sequence",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "phases" in data
    assert "total_phases" in data


@pytest.mark.asyncio
async def test_api_renovation_timeline(client, admin_user, sample_building, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_duration_weeks" in data
    assert "critical_path" in data


@pytest.mark.asyncio
async def test_api_parallel_tracks(client, admin_user, sample_building, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-parallel-tracks",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "tracks" in data
    assert "sequential_duration_weeks" in data


@pytest.mark.asyncio
async def test_api_readiness_blockers(client, admin_user, sample_building, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-readiness-blockers",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "blockers" in data
    assert "is_ready" in data


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    """Unauthenticated requests are rejected."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/renovation-sequence",
    )
    assert resp.status_code == 401
