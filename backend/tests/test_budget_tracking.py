"""Tests for budget tracking service + API."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from jose import jwt

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.budget_tracking_service import (
    forecast_quarterly_spend,
    get_building_budget_overview,
    get_portfolio_budget_summary,
    track_cost_variance,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
async def org_admin(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="orgadmin@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="Admin",
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
async def building_with_data(db_session, org_admin):
    """Building with diagnostics, samples, and interventions."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Budget 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        surface_area_m2=300.0,
        created_by=org_admin.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=bldg.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    # Two samples: asbestos exceeded, lead exceeded
    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        pollutant_type="lead",
        threshold_exceeded=True,
        risk_level="medium",
    )
    db_session.add_all([s1, s2])
    await db_session.flush()

    # Interventions: one completed, one planned, one in_progress
    today = date.today()
    iv1 = Intervention(
        id=uuid.uuid4(),
        building_id=bldg.id,
        intervention_type="remediation",
        title="Asbestos removal phase 1",
        status="completed",
        cost_chf=15000.0,
        date_start=today - timedelta(days=90),
        date_end=today - timedelta(days=60),
        created_by=org_admin.id,
    )
    iv2 = Intervention(
        id=uuid.uuid4(),
        building_id=bldg.id,
        intervention_type="remediation",
        title="Asbestos removal phase 2",
        status="planned",
        cost_chf=20000.0,
        date_start=today + timedelta(days=30),
        created_by=org_admin.id,
    )
    iv3 = Intervention(
        id=uuid.uuid4(),
        building_id=bldg.id,
        intervention_type="monitoring",
        title="Air quality monitoring",
        status="in_progress",
        cost_chf=3000.0,
        date_start=today - timedelta(days=15),
        created_by=org_admin.id,
    )
    db_session.add_all([iv1, iv2, iv3])
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def empty_building(db_session, admin_user):
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2010,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# FN1 — get_building_budget_overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_overview_with_data(db_session, building_with_data):
    result = await get_building_budget_overview(db_session, building_with_data.id)

    assert result.building_id == building_with_data.id
    # Estimated = asbestos(120*300) + lead(80*300) = 36000 + 24000 = 60000
    assert result.estimated_total_cost_chf == 60000.0
    assert result.spent_chf == 15000.0
    assert result.remaining_chf == 45000.0
    assert result.burn_rate_chf_per_month > 0
    assert result.projected_completion_cost_chf > 0
    assert result.generated_at is not None


@pytest.mark.asyncio
async def test_budget_overview_empty_building(db_session, empty_building):
    result = await get_building_budget_overview(db_session, empty_building.id)

    assert result.estimated_total_cost_chf == 0.0
    assert result.spent_chf == 0.0
    assert result.remaining_chf == 0.0
    assert result.burn_rate_chf_per_month == 0.0
    assert result.status == "on_track"


@pytest.mark.asyncio
async def test_budget_overview_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_building_budget_overview(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_budget_overview_status_on_track(db_session, empty_building):
    result = await get_building_budget_overview(db_session, empty_building.id)
    assert result.status == "on_track"


# ---------------------------------------------------------------------------
# FN2 — track_cost_variance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_variance_with_data(db_session, building_with_data):
    result = await track_cost_variance(db_session, building_with_data.id)

    assert result.building_id == building_with_data.id
    assert len(result.items) == 3
    assert result.total_estimated_chf > 0

    # Check categories present
    categories = {item.cost_category for item in result.items}
    assert "remediation" in categories
    assert "monitoring" in categories


@pytest.mark.asyncio
async def test_cost_variance_completed_has_actual(db_session, building_with_data):
    result = await track_cost_variance(db_session, building_with_data.id)

    completed = [i for i in result.items if i.status == "completed"]
    assert len(completed) == 1
    assert completed[0].actual_cost_chf is not None


@pytest.mark.asyncio
async def test_cost_variance_planned_no_actual(db_session, building_with_data):
    result = await track_cost_variance(db_session, building_with_data.id)

    planned = [i for i in result.items if i.status == "planned"]
    assert len(planned) == 1
    assert planned[0].actual_cost_chf is None


@pytest.mark.asyncio
async def test_cost_variance_empty_building(db_session, empty_building):
    result = await track_cost_variance(db_session, empty_building.id)

    assert len(result.items) == 0
    assert result.total_estimated_chf == 0.0
    assert result.overrun_count == 0


@pytest.mark.asyncio
async def test_cost_variance_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await track_cost_variance(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_cost_variance_by_category(db_session, building_with_data):
    result = await track_cost_variance(db_session, building_with_data.id)

    assert "remediation" in result.by_category
    assert result.by_category["remediation"] > 0


# ---------------------------------------------------------------------------
# FN3 — forecast_quarterly_spend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quarterly_forecast_with_data(db_session, building_with_data):
    result = await forecast_quarterly_spend(db_session, building_with_data.id)

    assert result.building_id == building_with_data.id
    assert len(result.quarters) == 4
    assert result.total_projected_chf > 0


@pytest.mark.asyncio
async def test_quarterly_forecast_quarter_labels(db_session, building_with_data):
    result = await forecast_quarterly_spend(db_session, building_with_data.id)

    for q in result.quarters:
        assert q.quarter.startswith("20")
        assert "-Q" in q.quarter


@pytest.mark.asyncio
async def test_quarterly_forecast_empty(db_session, empty_building):
    result = await forecast_quarterly_spend(db_session, empty_building.id)

    assert len(result.quarters) == 4
    assert result.total_projected_chf == 0.0


@pytest.mark.asyncio
async def test_quarterly_forecast_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await forecast_quarterly_spend(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_budget_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_summary(db_session, org, building_with_data):
    result = await get_portfolio_budget_summary(db_session, org.id)

    assert result.organization_id == org.id
    assert result.total_estimated_chf > 0
    assert result.total_spent_chf == 15000.0
    assert len(result.buildings) == 1
    assert result.buildings[0].address == "Rue Budget 10"


@pytest.mark.asyncio
async def test_portfolio_summary_no_members(db_session):
    o = Organization(id=uuid.uuid4(), name="Empty Org", type="diagnostic_lab")
    db_session.add(o)
    await db_session.commit()

    result = await get_portfolio_budget_summary(db_session, o.id)

    assert result.total_estimated_chf == 0.0
    assert len(result.buildings) == 0


@pytest.mark.asyncio
async def test_portfolio_summary_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_portfolio_budget_summary(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_portfolio_summary_over_budget_flag(db_session, org, org_admin):
    """Building where spent > estimated should be flagged as over budget."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Overbudget 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2000,
        building_type="residential",
        surface_area_m2=100.0,
        created_by=org_admin.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    # No diagnostics → estimated = 0, but completed intervention with cost
    iv = Intervention(
        id=uuid.uuid4(),
        building_id=bldg.id,
        intervention_type="remediation",
        title="Unexpected work",
        status="completed",
        cost_chf=50000.0,
        created_by=org_admin.id,
    )
    db_session.add(iv)
    await db_session.commit()

    result = await get_portfolio_budget_summary(db_session, org.id)

    over_budget_items = [b for b in result.buildings if b.is_over_budget]
    assert result.buildings_over_budget >= 1
    assert len(over_budget_items) >= 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_budget_overview(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/budget-overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "estimated_total_cost_chf" in data


@pytest.mark.asyncio
async def test_api_budget_overview_404(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/budget-overview",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_cost_variance(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/cost-variance",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "items" in data


@pytest.mark.asyncio
async def test_api_quarterly_forecast(client, auth_headers, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/quarterly-forecast",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["quarters"]) == 4


@pytest.mark.asyncio
async def test_api_portfolio_summary(client, auth_headers, db_session):
    o = Organization(id=uuid.uuid4(), name="API Org", type="property_management")
    db_session.add(o)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/organizations/{o.id}/budget-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(o.id)


@pytest.mark.asyncio
async def test_api_portfolio_summary_404(client, auth_headers):
    resp = await client.get(
        f"/api/v1/organizations/{uuid.uuid4()}/budget-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/budget-overview",
    )
    assert resp.status_code in (401, 403)
