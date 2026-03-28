"""Tests for building life calendar service and API."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.building import Building
from app.models.contract import Contract
from app.models.diagnostic import Diagnostic
from app.models.insurance_policy import InsurancePolicy
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.user import User
from app.services.building_life_service import get_annual_review, get_building_calendar

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def bl_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="blife@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lg2HEOi6N5eFJOr7Yap0C.KHleKGJT/w4W6IaN5ZU6fNi",
        first_name="BLife",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def bl_building(db_session, bl_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vie 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=bl_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def bl_obligation(db_session, bl_building):
    today = date.today()
    ob = Obligation(
        id=uuid.uuid4(),
        building_id=bl_building.id,
        title="Controle annuel chaudiere",
        obligation_type="maintenance",
        due_date=today + timedelta(days=45),
        status="upcoming",
        priority="medium",
    )
    db_session.add(ob)
    await db_session.commit()
    await db_session.refresh(ob)
    return ob


@pytest.fixture
async def bl_overdue_obligation(db_session, bl_building):
    ob = Obligation(
        id=uuid.uuid4(),
        building_id=bl_building.id,
        title="Verification extincteurs",
        obligation_type="regulatory_inspection",
        due_date=date.today() - timedelta(days=10),
        status="overdue",
        priority="high",
    )
    db_session.add(ob)
    await db_session.commit()
    await db_session.refresh(ob)
    return ob


@pytest.fixture
async def bl_contract(db_session, bl_building, bl_user):
    ctr = Contract(
        id=uuid.uuid4(),
        building_id=bl_building.id,
        contract_type="maintenance",
        reference_code="CTR-LIFE-001",
        title="Contrat entretien ascenseur",
        counterparty_type="organization",
        counterparty_id=uuid.uuid4(),
        date_start=date(2024, 1, 1),
        date_end=date.today() + timedelta(days=60),
        auto_renewal=True,
        notice_period_months=3,
        status="active",
        created_by=bl_user.id,
    )
    db_session.add(ctr)
    await db_session.commit()
    await db_session.refresh(ctr)
    return ctr


@pytest.fixture
async def bl_insurance(db_session, bl_building, bl_user):
    pol = InsurancePolicy(
        id=uuid.uuid4(),
        building_id=bl_building.id,
        policy_type="building_eca",
        policy_number=f"POL-LIFE-{uuid.uuid4().hex[:6]}",
        insurer_name="ECA Vaud",
        date_start=date(2024, 1, 1),
        date_end=date.today() + timedelta(days=90),
        status="active",
        created_by=bl_user.id,
    )
    db_session.add(pol)
    await db_session.commit()
    await db_session.refresh(pol)
    return pol


@pytest.fixture
async def bl_lease(db_session, bl_building, bl_user):
    le = Lease(
        id=uuid.uuid4(),
        building_id=bl_building.id,
        lease_type="residential",
        reference_code="BAIL-LIFE-001",
        tenant_type="contact",
        tenant_id=uuid.uuid4(),
        date_start=date(2023, 4, 1),
        date_end=date.today() + timedelta(days=120),
        notice_period_months=3,
        status="active",
        created_by=bl_user.id,
    )
    db_session.add(le)
    await db_session.commit()
    await db_session.refresh(le)
    return le


@pytest.fixture
async def bl_diagnostic(db_session, bl_building):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=bl_building.id,
        diagnostic_type="asbestos",
        status="completed",
        date_inspection=date(2024, 3, 1),
        date_report=date(2024, 3, 15),
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calendar_empty_building(db_session, bl_building):
    """Calendar returns empty events for building with no data."""
    result = await get_building_calendar(db_session, bl_building.id)
    assert result is not None
    assert result["summary"]["total_events"] == 0
    assert result["events"] == []


@pytest.mark.asyncio
async def test_calendar_returns_none_for_missing_building(db_session):
    """Calendar returns None for non-existent building."""
    result = await get_building_calendar(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_calendar_collects_obligations(db_session, bl_building, bl_obligation):
    """Calendar includes obligation events."""
    result = await get_building_calendar(db_session, bl_building.id)
    assert result["summary"]["total_events"] >= 1
    types = [e["type"] for e in result["events"]]
    assert "obligation" in types


@pytest.mark.asyncio
async def test_calendar_collects_overdue(db_session, bl_building, bl_overdue_obligation):
    """Calendar counts overdue events correctly."""
    result = await get_building_calendar(db_session, bl_building.id)
    assert result["summary"]["overdue"] >= 1
    overdue = [e for e in result["events"] if e["status"] == "overdue"]
    assert len(overdue) >= 1
    assert overdue[0]["priority"] == "critical"


@pytest.mark.asyncio
async def test_calendar_collects_contracts(db_session, bl_building, bl_contract):
    """Calendar includes contract end and notice events."""
    result = await get_building_calendar(db_session, bl_building.id)
    types = [e["type"] for e in result["events"]]
    assert "contract" in types
    # Should have both end date and notice period events
    contract_events = [e for e in result["events"] if e["type"] == "contract"]
    assert len(contract_events) >= 1


@pytest.mark.asyncio
async def test_calendar_collects_insurance(db_session, bl_building, bl_insurance):
    """Calendar includes insurance renewal events."""
    result = await get_building_calendar(db_session, bl_building.id)
    types = [e["type"] for e in result["events"]]
    assert "insurance" in types


@pytest.mark.asyncio
async def test_calendar_collects_leases(db_session, bl_building, bl_lease):
    """Calendar includes lease end and notice events."""
    result = await get_building_calendar(db_session, bl_building.id)
    types = [e["type"] for e in result["events"]]
    assert "lease" in types


@pytest.mark.asyncio
async def test_calendar_collects_diagnostic_expiry(db_session, bl_building, bl_diagnostic):
    """Calendar includes diagnostic expiry events."""
    result = await get_building_calendar(db_session, bl_building.id, horizon_days=1095)
    types = [e["type"] for e in result["events"]]
    assert "diagnostic_expiry" in types


@pytest.mark.asyncio
async def test_calendar_by_month_grouping(db_session, bl_building, bl_obligation, bl_contract):
    """Calendar groups events by month."""
    result = await get_building_calendar(db_session, bl_building.id)
    assert "by_month" in result
    assert isinstance(result["by_month"], dict)
    # At least one month should have events
    total_in_months = sum(len(v) for v in result["by_month"].values())
    assert total_in_months == result["summary"]["total_events"]


@pytest.mark.asyncio
async def test_calendar_events_sorted_by_date(db_session, bl_building, bl_obligation, bl_contract, bl_insurance):
    """Calendar events are sorted chronologically."""
    result = await get_building_calendar(db_session, bl_building.id)
    dates = [e["date"] for e in result["events"]]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_calendar_action_required(db_session, bl_building, bl_obligation):
    """Every event has an action_required field."""
    result = await get_building_calendar(db_session, bl_building.id)
    for event in result["events"]:
        assert event["action_required"] is not None
        assert len(event["action_required"]) > 0


# ---------------------------------------------------------------------------
# Annual review tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_annual_review_empty(db_session, bl_building):
    """Annual review works on empty building."""
    result = await get_annual_review(db_session, bl_building.id)
    assert result is not None
    assert result["diagnostics"]["valid"] == 0
    assert result["interventions_completed"] == 0
    assert len(result["recommendations"]) >= 1


@pytest.mark.asyncio
async def test_annual_review_returns_none_for_missing(db_session):
    """Annual review returns None for non-existent building."""
    result = await get_annual_review(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_annual_review_with_data(db_session, bl_building, bl_diagnostic, bl_obligation, bl_insurance):
    """Annual review includes data from multiple sources."""
    result = await get_annual_review(db_session, bl_building.id)
    assert result is not None
    assert "diagnostics" in result
    assert "insurance_coverage" in result
    assert "recommendations" in result
    assert result["insurance_coverage"]["active_policies"] >= 1


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_calendar(client: AsyncClient, auth_headers, bl_building):
    """GET /buildings/{id}/calendar returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{bl_building.id}/calendar",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert "summary" in data
    assert "by_month" in data


@pytest.mark.asyncio
async def test_api_calendar_404(client: AsyncClient, auth_headers):
    """GET /buildings/{id}/calendar returns 404 for missing building."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/calendar",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_annual_review(client: AsyncClient, auth_headers, bl_building):
    """GET /buildings/{id}/annual-review returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{bl_building.id}/annual-review",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "diagnostics" in data
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_api_annual_review_404(client: AsyncClient, auth_headers):
    """GET /buildings/{id}/annual-review returns 404 for missing building."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/annual-review",
        headers=auth_headers,
    )
    assert resp.status_code == 404
