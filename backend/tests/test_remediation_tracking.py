"""Tests for Remediation Tracking service and API."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.services.remediation_tracking_service import (
    estimate_remediation_timeline,
    get_portfolio_remediation_dashboard,
    get_remediation_cost_tracker,
    get_remediation_status,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_user(db_session, org):
    user = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash="$2b$12$LJ3m4ys3LG3RqS0B4JQB4e1GJr0Fq1JXS6JGR5R1P0Y6Y6Y6Y6Y6",
        first_name="Org",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def building_with_org(db_session, org_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Remediation 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def completed_diagnostic(db_session, sample_building):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


@pytest.fixture
async def asbestos_sample(db_session, completed_diagnostic):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=completed_diagnostic.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
        location_detail="Kitchen ceiling",
        material_category="insulation",
        material_state="friable",
        concentration=5.0,
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)
    return sample


@pytest.fixture
async def pcb_sample(db_session, completed_diagnostic):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=completed_diagnostic.id,
        sample_number="S-002",
        pollutant_type="pcb",
        threshold_exceeded=True,
        risk_level="medium",
        location_detail="Window joints",
        concentration=120.0,
        unit="mg/kg",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)
    return sample


@pytest.fixture
async def lead_sample(db_session, completed_diagnostic):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=completed_diagnostic.id,
        sample_number="S-003",
        pollutant_type="lead",
        threshold_exceeded=True,
        risk_level="medium",
        location_detail="Bathroom paint",
        concentration=6000.0,
        unit="mg/kg",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)
    return sample


@pytest.fixture
async def zone_for_building(db_session, sample_building, admin_user):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        zone_type="room",
        name="Kitchen",
        created_by=admin_user.id,
    )
    db_session.add(zone)
    await db_session.commit()
    await db_session.refresh(zone)
    return zone


@pytest.fixture
async def completed_asbestos_intervention(db_session, sample_building, admin_user):
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="asbestos_removal",
        title="Asbestos removal - kitchen",
        status="completed",
        cost_chf=45_000.0,
        date_start=date.today() - timedelta(days=30),
        date_end=date.today() - timedelta(days=5),
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()
    await db_session.refresh(iv)
    return iv


@pytest.fixture
async def in_progress_pcb_intervention(db_session, sample_building, admin_user):
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="pcb_decontamination",
        title="PCB removal - joints",
        status="in_progress",
        cost_chf=30_000.0,
        date_start=date.today() - timedelta(days=10),
        date_end=date.today() + timedelta(days=20),
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()
    await db_session.refresh(iv)
    return iv


@pytest.fixture
async def overdue_action(db_session, sample_building, completed_diagnostic):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_id=completed_diagnostic.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Remove asbestos insulation",
        priority="high",
        status="open",
        due_date=date.today() - timedelta(days=10),
        metadata_json={"pollutant_type": "asbestos"},
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


# ---------------------------------------------------------------------------
# FN1: get_remediation_status tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remediation_status_no_pollutants(db_session, sample_building):
    """Building with no diagnostics returns empty pollutants."""
    result = await get_remediation_status(sample_building.id, db_session)
    assert result.building_id == sample_building.id
    assert result.pollutants == []
    assert result.overall_progress_percentage == 0.0


@pytest.mark.asyncio
async def test_remediation_status_building_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await get_remediation_status(uuid.uuid4(), db_session)


@pytest.mark.asyncio
async def test_remediation_status_with_asbestos(db_session, sample_building, asbestos_sample):
    """Building with positive asbestos sample shows pending status."""
    result = await get_remediation_status(sample_building.id, db_session)
    assert len(result.pollutants) == 1
    p = result.pollutants[0]
    assert p.pollutant_type == "asbestos"
    assert p.status == "pending"
    assert p.affected_zones >= 1
    assert p.progress_percentage == 0.0


@pytest.mark.asyncio
async def test_remediation_status_completed_intervention(
    db_session, sample_building, asbestos_sample, completed_asbestos_intervention
):
    """Completed intervention marks pollutant as completed/verified."""
    result = await get_remediation_status(sample_building.id, db_session)
    asbestos = next(p for p in result.pollutants if p.pollutant_type == "asbestos")
    assert asbestos.status in ("completed", "verified")
    assert asbestos.progress_percentage == 100.0


@pytest.mark.asyncio
async def test_remediation_status_in_progress(db_session, sample_building, pcb_sample, in_progress_pcb_intervention):
    """In-progress intervention shows in_progress status."""
    result = await get_remediation_status(sample_building.id, db_session)
    pcb = next(p for p in result.pollutants if p.pollutant_type == "pcb")
    assert pcb.status == "in_progress"


@pytest.mark.asyncio
async def test_remediation_status_multiple_pollutants(
    db_session, sample_building, asbestos_sample, pcb_sample, lead_sample
):
    """Multiple pollutants are tracked independently."""
    result = await get_remediation_status(sample_building.id, db_session)
    assert len(result.pollutants) == 3
    types = {p.pollutant_type for p in result.pollutants}
    assert types == {"asbestos", "pcb", "lead"}


@pytest.mark.asyncio
async def test_remediation_status_blocking_issues(db_session, sample_building, asbestos_sample, overdue_action):
    """Overdue actions show up as blocking issues."""
    result = await get_remediation_status(sample_building.id, db_session)
    asbestos = next(p for p in result.pollutants if p.pollutant_type == "asbestos")
    assert len(asbestos.blocking_issues) > 0
    assert any("Overdue" in issue for issue in asbestos.blocking_issues)


@pytest.mark.asyncio
async def test_remediation_status_with_zones(db_session, sample_building, asbestos_sample, zone_for_building):
    """Zone count influences affected_zones calculation."""
    result = await get_remediation_status(sample_building.id, db_session)
    asbestos = next(p for p in result.pollutants if p.pollutant_type == "asbestos")
    assert asbestos.affected_zones >= 1


# ---------------------------------------------------------------------------
# FN2: estimate_remediation_timeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_no_pollutants(db_session, sample_building):
    """Building with no issues returns empty timelines."""
    result = await estimate_remediation_timeline(sample_building.id, db_session)
    assert result.building_id == sample_building.id
    assert result.timelines == []


@pytest.mark.asyncio
async def test_timeline_building_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await estimate_remediation_timeline(uuid.uuid4(), db_session)


@pytest.mark.asyncio
async def test_timeline_single_pollutant(db_session, sample_building, asbestos_sample):
    """Single pollutant gets a timeline with duration."""
    result = await estimate_remediation_timeline(sample_building.id, db_session)
    assert len(result.timelines) == 1
    t = result.timelines[0]
    assert t.pollutant_type == "asbestos"
    assert t.duration_days > 0
    assert t.estimated_start is not None
    assert t.estimated_completion is not None
    assert t.estimated_completion > t.estimated_start


@pytest.mark.asyncio
async def test_timeline_dependencies(db_session, sample_building, asbestos_sample, pcb_sample):
    """PCB depends on asbestos — PCB starts after asbestos completes."""
    result = await estimate_remediation_timeline(sample_building.id, db_session)
    asbestos_tl = next(t for t in result.timelines if t.pollutant_type == "asbestos")
    pcb_tl = next(t for t in result.timelines if t.pollutant_type == "pcb")
    assert "asbestos" in pcb_tl.dependencies
    assert pcb_tl.estimated_start >= asbestos_tl.estimated_completion


@pytest.mark.asyncio
async def test_timeline_parallel_possible(db_session, sample_building, completed_diagnostic):
    """Radon can run parallel with asbestos."""
    radon_sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=completed_diagnostic.id,
        sample_number="S-RADON",
        pollutant_type="radon",
        threshold_exceeded=True,
        risk_level="high",
        location_detail="Basement",
        concentration=500.0,
        unit="Bq/m3",
    )
    asb_sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=completed_diagnostic.id,
        sample_number="S-ASB",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
        location_detail="Ceiling",
    )
    db_session.add_all([radon_sample, asb_sample])
    await db_session.commit()

    result = await estimate_remediation_timeline(sample_building.id, db_session)
    radon_tl = next(t for t in result.timelines if t.pollutant_type == "radon")
    assert radon_tl.parallel_possible is True


@pytest.mark.asyncio
async def test_timeline_uses_intervention_dates(db_session, sample_building, pcb_sample, in_progress_pcb_intervention):
    """Timeline uses actual intervention dates when available."""
    result = await estimate_remediation_timeline(sample_building.id, db_session)
    pcb_tl = next(t for t in result.timelines if t.pollutant_type == "pcb")
    assert pcb_tl.estimated_start == in_progress_pcb_intervention.date_start


# ---------------------------------------------------------------------------
# FN3: get_remediation_cost_tracker tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_tracker_no_pollutants(db_session, sample_building):
    """Building with no issues returns empty costs."""
    result = await get_remediation_cost_tracker(sample_building.id, db_session)
    assert result.building_id == sample_building.id
    assert result.costs == []
    assert result.total_estimated == 0.0


@pytest.mark.asyncio
async def test_cost_tracker_building_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await get_remediation_cost_tracker(uuid.uuid4(), db_session)


@pytest.mark.asyncio
async def test_cost_tracker_estimated_costs(db_session, sample_building, asbestos_sample):
    """Pollutant gets default estimated cost."""
    result = await get_remediation_cost_tracker(sample_building.id, db_session)
    assert len(result.costs) == 1
    c = result.costs[0]
    assert c.pollutant_type == "asbestos"
    assert c.estimated_cost > 0
    assert c.actual_cost == 0.0
    assert c.budget_status == "on_track"
    assert len(c.breakdown_by_phase) >= 1


@pytest.mark.asyncio
async def test_cost_tracker_with_completed_intervention(
    db_session, sample_building, asbestos_sample, completed_asbestos_intervention
):
    """Completed intervention contributes actual cost."""
    result = await get_remediation_cost_tracker(sample_building.id, db_session)
    asbestos_cost = next(c for c in result.costs if c.pollutant_type == "asbestos")
    assert asbestos_cost.actual_cost == 45_000.0
    assert result.total_actual == 45_000.0


@pytest.mark.asyncio
async def test_cost_tracker_budget_over(db_session, sample_building, lead_sample, admin_user):
    """Over-budget intervention changes budget_status."""
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="lead_removal",
        title="Lead removal",
        status="completed",
        cost_chf=100_000.0,
        created_by=admin_user.id,
    )
    db_session.add(iv)
    await db_session.commit()

    result = await get_remediation_cost_tracker(sample_building.id, db_session)
    lead_cost = next(c for c in result.costs if c.pollutant_type == "lead")
    assert lead_cost.budget_status == "over"
    assert lead_cost.variance_percentage > 0


@pytest.mark.asyncio
async def test_cost_tracker_multiple_pollutants(db_session, sample_building, asbestos_sample, pcb_sample):
    """Multiple pollutants tracked independently."""
    result = await get_remediation_cost_tracker(sample_building.id, db_session)
    assert len(result.costs) == 2
    assert result.total_estimated > 0


# ---------------------------------------------------------------------------
# FN4: get_portfolio_remediation_dashboard tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_dashboard_empty_org(db_session, org):
    """Org with no buildings returns zero dashboard."""
    result = await get_portfolio_remediation_dashboard(org.id, db_session)
    assert result.organization_id == org.id
    assert result.total_buildings_needing_remediation == 0
    assert result.overall_progress_pct == 0.0


@pytest.mark.asyncio
async def test_portfolio_dashboard_no_pollutants(db_session, org, building_with_org):
    """Org buildings without pollutant issues return zero remediation count."""
    result = await get_portfolio_remediation_dashboard(org.id, db_session)
    assert result.total_buildings_needing_remediation == 0


@pytest.mark.asyncio
async def test_portfolio_dashboard_with_pollutants(db_session, org, org_user, building_with_org):
    """Org building with pollutant issues appears in dashboard."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_with_org.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="ORG-S1",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
        location_detail="Ceiling",
    )
    db_session.add(sample)
    await db_session.commit()

    result = await get_portfolio_remediation_dashboard(org.id, db_session)
    assert result.total_buildings_needing_remediation == 1
    assert len(result.by_pollutant_type) == 1
    assert result.by_pollutant_type[0].pollutant_type == "asbestos"
    assert result.estimated_total_cost > 0


@pytest.mark.asyncio
async def test_portfolio_dashboard_at_risk_buildings(db_session, org, org_user, building_with_org):
    """Buildings with overdue actions appear as at-risk."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_with_org.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="ORG-S2",
        pollutant_type="pcb",
        threshold_exceeded=True,
        risk_level="medium",
        location_detail="Joints",
    )
    db_session.add(sample)

    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building_with_org.id,
        diagnostic_id=diag.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Remove PCB joints",
        priority="high",
        status="open",
        due_date=date.today() - timedelta(days=5),
        metadata_json={"pollutant_type": "pcb"},
    )
    db_session.add(action)
    await db_session.commit()

    result = await get_portfolio_remediation_dashboard(org.id, db_session)
    assert len(result.buildings_at_risk_of_delay) == 1
    at_risk = result.buildings_at_risk_of_delay[0]
    assert at_risk.overdue_actions >= 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_remediation_status(client, auth_headers, sample_building):
    """GET /buildings/{id}/remediation-status returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/remediation-status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "pollutants" in data


@pytest.mark.asyncio
async def test_api_remediation_status_not_found(client, auth_headers):
    """GET /buildings/{id}/remediation-status returns 404 for missing building."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/remediation-status",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_remediation_timeline(client, auth_headers, sample_building):
    """GET /buildings/{id}/remediation-timeline returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/remediation-timeline",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_remediation_costs(client, auth_headers, sample_building):
    """GET /buildings/{id}/remediation-costs returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/remediation-cost-tracking",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_remediation_dashboard(client, auth_headers):
    """GET /organizations/{id}/remediation-dashboard returns 200."""
    org_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/organizations/{org_id}/remediation-dashboard",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org_id)


@pytest.mark.asyncio
async def test_api_remediation_status_unauthorized(client, sample_building):
    """GET without auth returns 401."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/remediation-status",
    )
    assert resp.status_code == 401
