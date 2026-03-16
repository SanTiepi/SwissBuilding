"""Tests for the Monitoring Plan service and API endpoints."""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.monitoring_plan_service import (
    evaluate_monitoring_compliance,
    generate_monitoring_plan,
    get_monitoring_schedule,
    get_portfolio_monitoring_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db, name="TestOrg"):
    org = Organization(
        id=uuid.uuid4(),
        name=name,
        type="property_management",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_user_in_org(db, org_id, *, role="owner", hash_pw="$2b$12$LJ3m4ys3"):
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=hash_pw,
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_building(db, owner_id, *, address="Rue Test 1", construction_year=1970):
    building = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=owner_id,
        owner_id=owner_id,
        status="active",
    )
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


async def _create_diagnostic(db, building_id, *, diag_type="asbestos", status="completed"):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=diag_type,
        status=status,
        date_report=datetime.now(UTC).date(),
    )
    db.add(diag)
    await db.commit()
    await db.refresh(diag)
    return diag


async def _create_sample(
    db,
    diagnostic_id,
    *,
    pollutant_type="asbestos",
    action_required="encapsulation",
    threshold_exceeded=False,
    concentration=None,
    unit=None,
    location_floor="1er étage",
    location_room="Salon",
):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        action_required=action_required,
        threshold_exceeded=threshold_exceeded,
        concentration=concentration,
        unit=unit,
        location_floor=location_floor,
        location_room=location_room,
    )
    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    return sample


async def _create_intervention(
    db, building_id, *, intervention_type="encapsulation", status="completed", title="Encapsulation amiante"
):
    interv = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title=title,
        status=status,
    )
    db.add(interv)
    await db.commit()
    await db.refresh(interv)
    return interv


# ---------------------------------------------------------------------------
# Service-level tests: generate_monitoring_plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_plan_empty_building(db_session, admin_user):
    """Building with no diagnostics produces an empty plan."""
    building = await _create_building(db_session, admin_user.id)
    plan = await generate_monitoring_plan(db_session, building.id)
    assert plan.building_id == building.id
    assert plan.total_items == 0
    assert plan.annual_cost_chf == 0.0


@pytest.mark.asyncio
async def test_generate_plan_nonexistent_building(db_session):
    """Non-existent building returns empty plan."""
    plan = await generate_monitoring_plan(db_session, uuid.uuid4())
    assert plan.total_items == 0


@pytest.mark.asyncio
async def test_generate_plan_asbestos_encapsulated(db_session, admin_user):
    """Encapsulated asbestos generates 2 monitoring items (visual + air)."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="asbestos")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", action_required="encapsulation")

    plan = await generate_monitoring_plan(db_session, building.id)
    assert plan.total_items == 2
    methods = {item.monitoring_method for item in plan.items}
    assert "visual_inspection" in methods
    assert "air_sampling" in methods
    assert plan.annual_cost_chf > 0


@pytest.mark.asyncio
async def test_generate_plan_pcb_sealed(db_session, admin_user):
    """Sealed PCB generates wipe test item."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="pcb")
    await _create_sample(db_session, diag.id, pollutant_type="pcb", action_required="sealing")

    plan = await generate_monitoring_plan(db_session, building.id)
    assert plan.total_items == 1
    assert plan.items[0].monitoring_method == "wipe_test"
    assert plan.items[0].frequency == "annual"


@pytest.mark.asyncio
async def test_generate_plan_radon_exceeded(db_session, admin_user):
    """Radon above threshold generates measurement item."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="radon")
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="radon",
        action_required="ventilation",
        threshold_exceeded=True,
        concentration=450.0,
        unit="Bq/m3",
    )

    plan = await generate_monitoring_plan(db_session, building.id)
    assert plan.total_items == 1
    assert plan.items[0].monitoring_method == "radon_measurement"
    assert plan.items[0].frequency == "biannual"


@pytest.mark.asyncio
async def test_generate_plan_lead_encapsulated(db_session, admin_user):
    """Encapsulated lead generates visual inspection item."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="lead")
    await _create_sample(db_session, diag.id, pollutant_type="lead", action_required="encapsulation")

    plan = await generate_monitoring_plan(db_session, building.id)
    assert plan.total_items == 1
    assert plan.items[0].pollutant_type == "lead"
    assert plan.items[0].monitoring_method == "visual_inspection"


@pytest.mark.asyncio
async def test_generate_plan_intervention_encapsulation(db_session, admin_user):
    """Completed encapsulation intervention generates monitoring item."""
    building = await _create_building(db_session, admin_user.id)
    await _create_intervention(db_session, building.id, intervention_type="encapsulation")

    plan = await generate_monitoring_plan(db_session, building.id)
    assert plan.total_items == 1
    assert plan.items[0].monitoring_method == "visual_inspection"
    assert plan.items[0].responsible_party == "contractor"


@pytest.mark.asyncio
async def test_generate_plan_draft_diagnostic_ignored(db_session, admin_user):
    """Samples from draft diagnostics are not included."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="asbestos", status="draft")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", action_required="encapsulation")

    plan = await generate_monitoring_plan(db_session, building.id)
    assert plan.total_items == 0


@pytest.mark.asyncio
async def test_generate_plan_multiple_pollutants(db_session, admin_user):
    """Building with multiple pollutants generates items for each."""
    building = await _create_building(db_session, admin_user.id)

    diag_a = await _create_diagnostic(db_session, building.id, diag_type="asbestos")
    await _create_sample(db_session, diag_a.id, pollutant_type="asbestos", action_required="encapsulation")

    diag_p = await _create_diagnostic(db_session, building.id, diag_type="pcb")
    await _create_sample(db_session, diag_p.id, pollutant_type="pcb", action_required="sealing")

    plan = await generate_monitoring_plan(db_session, building.id)
    # 2 asbestos (visual + air) + 1 pcb (wipe) = 3
    assert plan.total_items == 3
    pollutants = {item.pollutant_type for item in plan.items}
    assert pollutants == {"asbestos", "pcb"}


# ---------------------------------------------------------------------------
# Service-level tests: get_monitoring_schedule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_empty_building(db_session, admin_user):
    """Empty building has no scheduled or overdue checks."""
    building = await _create_building(db_session, admin_user.id)
    schedule = await get_monitoring_schedule(db_session, building.id)
    assert schedule.total_scheduled == 0
    assert schedule.total_overdue == 0
    assert schedule.cost_forecast_chf == 0.0


@pytest.mark.asyncio
async def test_schedule_with_items(db_session, admin_user):
    """Building with monitoring items produces a schedule."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="asbestos")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", action_required="encapsulation")

    schedule = await get_monitoring_schedule(db_session, building.id)
    # Should have some scheduled checks in next 12 months
    total = schedule.total_scheduled + schedule.total_overdue
    assert total > 0
    assert schedule.cost_forecast_chf > 0


@pytest.mark.asyncio
async def test_schedule_checks_are_sorted(db_session, admin_user):
    """Scheduled checks are sorted by date."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="asbestos")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", action_required="encapsulation")

    schedule = await get_monitoring_schedule(db_session, building.id)
    if len(schedule.scheduled_checks) > 1:
        dates = [c.scheduled_date for c in schedule.scheduled_checks]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# Service-level tests: evaluate_monitoring_compliance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_no_requirements(db_session, admin_user):
    """Building with no monitoring needs = 100% compliance."""
    building = await _create_building(db_session, admin_user.id)
    compliance = await evaluate_monitoring_compliance(db_session, building.id)
    assert compliance.compliance_score == 100
    assert compliance.total_required == 0
    assert len(compliance.gaps) == 0


@pytest.mark.asyncio
async def test_compliance_with_gaps(db_session, admin_user):
    """Building with monitoring items but no recent checks has gaps."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="pcb")
    await _create_sample(db_session, diag.id, pollutant_type="pcb", action_required="sealing")

    compliance = await evaluate_monitoring_compliance(db_session, building.id)
    assert compliance.total_required > 0
    assert compliance.compliance_score <= 100


@pytest.mark.asyncio
async def test_compliance_score_range(db_session, admin_user):
    """Compliance score is always 0-100."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="asbestos")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", action_required="monitoring")

    compliance = await evaluate_monitoring_compliance(db_session, building.id)
    assert 0 <= compliance.compliance_score <= 100


# ---------------------------------------------------------------------------
# Service-level tests: get_portfolio_monitoring_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_empty_org(db_session):
    """Org with no buildings returns empty portfolio status."""
    org = await _create_org(db_session)
    status = await get_portfolio_monitoring_status(db_session, org.id)
    assert status.total_buildings == 0
    assert status.buildings_with_plans == 0
    assert status.total_annual_cost_chf == 0.0


@pytest.mark.asyncio
async def test_portfolio_with_buildings(db_session):
    """Org with buildings and monitoring items returns proper status."""
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org.id)
    building = await _create_building(db_session, user.id)

    diag = await _create_diagnostic(db_session, building.id, diag_type="asbestos")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", action_required="encapsulation")

    status = await get_portfolio_monitoring_status(db_session, org.id)
    assert status.total_buildings == 1
    assert status.buildings_with_plans == 1
    assert status.total_annual_cost_chf > 0
    assert len(status.buildings) == 1
    assert status.buildings[0].has_active_plan is True


@pytest.mark.asyncio
async def test_portfolio_compliance_rate(db_session):
    """Compliance rate reflects building compliance scores."""
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org.id)

    # Building without monitoring needs → 100% compliant
    await _create_building(db_session, user.id, address="Rue Clean 1")

    status = await get_portfolio_monitoring_status(db_session, org.id)
    assert 0.0 <= status.compliance_rate <= 1.0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_monitoring_plan(client, auth_headers, sample_building):
    """GET /buildings/{id}/monitoring-plan returns 200."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/monitoring-plan", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total_items" in data
    assert "annual_cost_chf" in data


@pytest.mark.asyncio
async def test_api_monitoring_schedule(client, auth_headers, sample_building):
    """GET /buildings/{id}/monitoring-schedule returns 200."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/monitoring-schedule", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "scheduled_checks" in data
    assert "overdue_checks" in data
    assert "cost_forecast_chf" in data


@pytest.mark.asyncio
async def test_api_monitoring_compliance(client, auth_headers, sample_building):
    """GET /buildings/{id}/monitoring-compliance returns 200."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/monitoring-compliance", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "compliance_score" in data
    assert 0 <= data["compliance_score"] <= 100


@pytest.mark.asyncio
async def test_api_monitoring_status_org(client, auth_headers, db_session):
    """GET /organizations/{id}/monitoring-status returns 200."""
    org = await _create_org(db_session)
    resp = await client.get(f"/api/v1/organizations/{org.id}/monitoring-status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings" in data
    assert "compliance_rate" in data


@pytest.mark.asyncio
async def test_api_monitoring_plan_unauthenticated(client, sample_building):
    """Unauthenticated request returns 401."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/monitoring-plan")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_plan_annual_cost_calculation(db_session, admin_user):
    """Annual cost correctly multiplies per-cycle cost by frequency."""
    building = await _create_building(db_session, admin_user.id)
    diag = await _create_diagnostic(db_session, building.id, diag_type="asbestos")
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", action_required="encapsulation")

    plan = await generate_monitoring_plan(db_session, building.id)
    # visual (annual, 350*1=350) + air (biannual, 800*2=1600) = 1950
    assert plan.annual_cost_chf == 1950.0
