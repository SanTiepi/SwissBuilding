"""Tests for building lifecycle service and API."""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.post_works_state import PostWorksState
from app.models.user import User
from app.services.building_lifecycle_service import (
    PHASES,
    get_lifecycle_phase,
    get_lifecycle_timeline,
    get_portfolio_lifecycle_distribution,
    predict_next_phase,
)

# ─── Helper fixtures ─────────────────────────────────────────────────


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def org_building(db_session, org_user):
    b = Building(
        id=uuid.uuid4(),
        address="Lifecycle Street 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


async def _add_diagnostic(db_session, building_id, status="draft", date_report=None):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status=status,
        date_report=date_report,
    )
    db_session.add(d)
    await db_session.commit()
    return d


async def _add_intervention(db_session, building_id, status="planned", date_start=None, date_end=None):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="removal",
        title="Test intervention",
        status=status,
        date_start=date_start,
        date_end=date_end,
    )
    db_session.add(i)
    await db_session.commit()
    return i


async def _add_artefact(db_session, building_id, status="draft", artefact_type="permit", acknowledged_at=None):
    a = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=building_id,
        artefact_type=artefact_type,
        status=status,
        title="Test artefact",
        acknowledged_at=acknowledged_at,
    )
    db_session.add(a)
    await db_session.commit()
    return a


async def _add_post_works(db_session, building_id, verified=False, verified_at=None):
    p = PostWorksState(
        id=uuid.uuid4(),
        building_id=building_id,
        state_type="removal_complete",
        title="Test post-works",
        verified=verified,
        verified_at=verified_at,
    )
    db_session.add(p)
    await db_session.commit()
    return p


# ─── Service tests: get_lifecycle_phase ──────────────────────────────


@pytest.mark.asyncio
async def test_phase_unknown_no_diagnostics(db_session, sample_building):
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result is not None
    assert result["phase"] == "unknown"
    assert result["phase_label"] == "Unknown"


@pytest.mark.asyncio
async def test_phase_assessed_draft_diagnostic(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="draft")
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result["phase"] == "assessed"


@pytest.mark.asyncio
async def test_phase_diagnosed_completed_diagnostic(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="completed")
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result["phase"] == "diagnosed"


@pytest.mark.asyncio
async def test_phase_planned_with_intervention(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="completed")
    await _add_intervention(db_session, sample_building.id, status="planned")
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result["phase"] == "planned"


@pytest.mark.asyncio
async def test_phase_in_remediation(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="completed")
    await _add_intervention(db_session, sample_building.id, status="in_progress")
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result["phase"] == "in_remediation"


@pytest.mark.asyncio
async def test_phase_cleared(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="validated")
    await _add_intervention(db_session, sample_building.id, status="completed")
    await _add_artefact(db_session, sample_building.id, status="approved")
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result["phase"] == "cleared"


@pytest.mark.asyncio
async def test_phase_cleared_via_post_works(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="validated")
    await _add_intervention(db_session, sample_building.id, status="completed")
    await _add_post_works(db_session, sample_building.id, verified=True, verified_at=datetime.now(UTC))
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result["phase"] == "cleared"


@pytest.mark.asyncio
async def test_phase_monitored(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="validated")
    await _add_intervention(db_session, sample_building.id, status="completed")
    await _add_artefact(db_session, sample_building.id, status="approved")
    await _add_artefact(db_session, sample_building.id, status="active", artefact_type="monitoring_plan")
    result = await get_lifecycle_phase(db_session, sample_building.id)
    assert result["phase"] == "monitored"


@pytest.mark.asyncio
async def test_phase_not_found(db_session):
    result = await get_lifecycle_phase(db_session, uuid.uuid4())
    assert result is None


# ─── Service tests: get_lifecycle_timeline ───────────────────────────


@pytest.mark.asyncio
async def test_timeline_empty_building(db_session, sample_building):
    result = await get_lifecycle_timeline(db_session, sample_building.id)
    assert result is not None
    assert result["current_phase"] == "unknown"
    assert len(result["transitions"]) == 1
    assert result["transitions"][0]["phase"] == "unknown"


@pytest.mark.asyncio
async def test_timeline_with_transitions(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="completed")
    await _add_intervention(db_session, sample_building.id, status="planned")
    result = await get_lifecycle_timeline(db_session, sample_building.id)
    assert result["current_phase"] == "planned"
    assert len(result["transitions"]) >= 3  # unknown → assessed → diagnosed → planned
    phases = [t["phase"] for t in result["transitions"]]
    assert "unknown" in phases
    assert "assessed" in phases
    assert "diagnosed" in phases
    assert "planned" in phases


@pytest.mark.asyncio
async def test_timeline_duration_tracking(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="draft")
    result = await get_lifecycle_timeline(db_session, sample_building.id)
    for t in result["transitions"]:
        assert t["duration_days"] >= 0


@pytest.mark.asyncio
async def test_timeline_not_found(db_session):
    result = await get_lifecycle_timeline(db_session, uuid.uuid4())
    assert result is None


# ─── Service tests: predict_next_phase ───────────────────────────────


@pytest.mark.asyncio
async def test_predict_from_unknown(db_session, sample_building):
    result = await predict_next_phase(db_session, sample_building.id)
    assert result["current_phase"] == "unknown"
    assert result["next_phase"] == "assessed"
    assert result["conditions_total"] >= 1
    assert result["conditions_met"] == 0
    assert result["estimated_days_to_transition"] == 14


@pytest.mark.asyncio
async def test_predict_from_assessed(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="draft")
    result = await predict_next_phase(db_session, sample_building.id)
    assert result["current_phase"] == "assessed"
    assert result["next_phase"] == "diagnosed"
    assert result["conditions_met"] == 0


@pytest.mark.asyncio
async def test_predict_from_diagnosed(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="completed")
    result = await predict_next_phase(db_session, sample_building.id)
    assert result["current_phase"] == "diagnosed"
    assert result["next_phase"] == "planned"


@pytest.mark.asyncio
async def test_predict_from_monitored_terminal(db_session, sample_building):
    await _add_diagnostic(db_session, sample_building.id, status="validated")
    await _add_intervention(db_session, sample_building.id, status="completed")
    await _add_artefact(db_session, sample_building.id, status="approved")
    await _add_artefact(db_session, sample_building.id, status="active", artefact_type="monitoring_plan")
    result = await predict_next_phase(db_session, sample_building.id)
    assert result["current_phase"] == "monitored"
    assert result["next_phase"] is None
    assert result["conditions_total"] == 0


@pytest.mark.asyncio
async def test_predict_not_found(db_session):
    result = await predict_next_phase(db_session, uuid.uuid4())
    assert result is None


# ─── Service tests: get_portfolio_lifecycle_distribution ─────────────


@pytest.mark.asyncio
async def test_portfolio_distribution_empty(db_session, org):
    result = await get_portfolio_lifecycle_distribution(db_session, org.id)
    assert result is not None
    assert result["total_buildings"] == 0
    assert len(result["distribution"]) == len(PHASES)


@pytest.mark.asyncio
async def test_portfolio_distribution_with_buildings(db_session, org, org_user):
    # Create two buildings — one unknown, one assessed
    b1 = Building(
        id=uuid.uuid4(),
        address="Dist 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    b2 = Building(
        id=uuid.uuid4(),
        address="Dist 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    await _add_diagnostic(db_session, b2.id, status="draft")

    result = await get_portfolio_lifecycle_distribution(db_session, org.id)
    assert result["total_buildings"] == 2

    phase_map = {d["phase"]: d["count"] for d in result["distribution"]}
    assert phase_map["unknown"] == 1
    assert phase_map["assessed"] == 1


@pytest.mark.asyncio
async def test_portfolio_distribution_bottleneck(db_session, org, org_user):
    # Create 3 buildings all stuck at assessed
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Bottleneck {i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=org_user.id,
            status="active",
        )
        db_session.add(b)
        await db_session.commit()
        await _add_diagnostic(db_session, b.id, status="draft")

    result = await get_portfolio_lifecycle_distribution(db_session, org.id)
    assert result["bottleneck_phase"] == "assessed"
    assert result["bottleneck_count"] == 3


@pytest.mark.asyncio
async def test_portfolio_distribution_org_not_found(db_session):
    result = await get_portfolio_lifecycle_distribution(db_session, uuid.uuid4())
    assert result is None


# ─── API endpoint tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_lifecycle_phase(client, sample_building, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/lifecycle-phase", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == "unknown"
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_lifecycle_phase_404(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/lifecycle-phase", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_lifecycle_timeline(client, sample_building, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/lifecycle-timeline", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_phase"] == "unknown"
    assert len(data["transitions"]) >= 1


@pytest.mark.asyncio
async def test_api_lifecycle_prediction(client, sample_building, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/lifecycle-prediction", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_phase"] == "unknown"
    assert data["next_phase"] == "assessed"


@pytest.mark.asyncio
async def test_api_lifecycle_prediction_401(client, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/lifecycle-prediction")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_portfolio_distribution(client, auth_headers, db_session, org, org_user):
    resp = await client.get(f"/api/v1/organizations/{org.id}/lifecycle-distribution", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] == 0
    assert len(data["distribution"]) == len(PHASES)


@pytest.mark.asyncio
async def test_api_portfolio_distribution_404(client, auth_headers):
    resp = await client.get(f"/api/v1/organizations/{uuid.uuid4()}/lifecycle-distribution", headers=auth_headers)
    assert resp.status_code == 404
