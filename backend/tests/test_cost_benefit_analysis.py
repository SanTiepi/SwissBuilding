"""Tests for cost-benefit analysis service and API."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.cost_benefit_analysis_service import (
    analyze_intervention_roi,
    calculate_inaction_cost,
    compare_remediation_strategies,
    get_portfolio_investment_plan,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(
        id=uuid.uuid4(),
        name="Test Régie SA",
        type="property_management",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session: AsyncSession, org: Organization) -> User:
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
async def building_with_samples(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with completed diagnostic and pollutant samples."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Test 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        surface_area_m2=500.0,
        floors_above=3,
        floors_below=1,
        created_by=admin_user.id,
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

    # Asbestos sample — critical, threshold exceeded
    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        risk_level="critical",
        threshold_exceeded=True,
        cfst_work_category="major",
        waste_disposal_type="special",
    )
    # PCB sample — high, threshold exceeded
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S002",
        pollutant_type="pcb",
        risk_level="high",
        threshold_exceeded=True,
    )
    # Lead sample — medium, threshold NOT exceeded
    s3 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S003",
        pollutant_type="lead",
        risk_level="medium",
        threshold_exceeded=False,
    )
    db_session.add_all([s1, s2, s3])
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_no_samples(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with no diagnostics."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1200",
        city="Genève",
        canton="GE",
        construction_year=2010,
        building_type="commercial",
        surface_area_m2=300.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# FN1 — analyze_intervention_roi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervention_roi_with_samples(db_session: AsyncSession, building_with_samples: Building):
    result = await analyze_intervention_roi(db_session, building_with_samples.id)
    assert result.building_id == building_with_samples.id
    assert result.discount_rate == 0.03
    # Only threshold-exceeded pollutants (asbestos, pcb) — not lead
    assert len(result.interventions) == 2
    pollutants = {i.pollutant_type for i in result.interventions}
    assert "asbestos" in pollutants
    assert "pcb" in pollutants
    assert "lead" not in pollutants


@pytest.mark.asyncio
async def test_intervention_roi_sorted_by_priority(db_session: AsyncSession, building_with_samples: Building):
    result = await analyze_intervention_roi(db_session, building_with_samples.id)
    scores = [i.priority_score for i in result.interventions]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_intervention_roi_npv_positive_for_critical(db_session: AsyncSession, building_with_samples: Building):
    result = await analyze_intervention_roi(db_session, building_with_samples.id)
    # At least the critical asbestos intervention should have positive NPV
    asbestos = next(i for i in result.interventions if i.pollutant_type == "asbestos")
    assert asbestos.npv_chf > 0


@pytest.mark.asyncio
async def test_intervention_roi_costs_positive(db_session: AsyncSession, building_with_samples: Building):
    result = await analyze_intervention_roi(db_session, building_with_samples.id)
    for intervention in result.interventions:
        assert intervention.estimated_cost_chf > 0
        assert intervention.risk_reduction_value_chf > 0
        assert intervention.payback_years > 0


@pytest.mark.asyncio
async def test_intervention_roi_empty_building(db_session: AsyncSession, building_no_samples: Building):
    result = await analyze_intervention_roi(db_session, building_no_samples.id)
    assert result.interventions == []


@pytest.mark.asyncio
async def test_intervention_roi_not_found(db_session: AsyncSession):
    with pytest.raises(ValueError, match="not found"):
        await analyze_intervention_roi(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN2 — compare_remediation_strategies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_strategies_three_returned(db_session: AsyncSession, building_with_samples: Building):
    result = await compare_remediation_strategies(db_session, building_with_samples.id)
    assert len(result.strategies) == 3
    names = [s.strategy for s in result.strategies]
    assert names == ["minimal", "standard", "comprehensive"]


@pytest.mark.asyncio
async def test_strategies_cost_ordering(db_session: AsyncSession, building_with_samples: Building):
    result = await compare_remediation_strategies(db_session, building_with_samples.id)
    costs = [s.total_cost_chf for s in result.strategies]
    assert costs[0] <= costs[1] <= costs[2]


@pytest.mark.asyncio
async def test_strategies_comprehensive_100_pct(db_session: AsyncSession, building_with_samples: Building):
    result = await compare_remediation_strategies(db_session, building_with_samples.id)
    comprehensive = result.strategies[2]
    assert comprehensive.risk_reduction_pct == 100.0
    assert comprehensive.residual_risk_level == "low"


@pytest.mark.asyncio
async def test_strategies_minimal_addresses_critical(db_session: AsyncSession, building_with_samples: Building):
    result = await compare_remediation_strategies(db_session, building_with_samples.id)
    minimal = result.strategies[0]
    # Critical pollutants: asbestos (critical) and pcb (high) should be in critical set
    assert "asbestos" in minimal.pollutants_addressed


@pytest.mark.asyncio
async def test_strategies_empty_building(db_session: AsyncSession, building_no_samples: Building):
    result = await compare_remediation_strategies(db_session, building_no_samples.id)
    assert len(result.strategies) == 3
    for s in result.strategies:
        assert s.total_cost_chf == 0.0


# ---------------------------------------------------------------------------
# FN3 — calculate_inaction_cost
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inaction_cost_with_violations(db_session: AsyncSession, building_with_samples: Building):
    result = await calculate_inaction_cost(db_session, building_with_samples.id)
    assert result.building_id == building_with_samples.id
    assert result.regulatory_fine_min_chf > 0
    assert result.regulatory_fine_max_chf >= result.regulatory_fine_min_chf
    assert result.liability_exposure_chf_per_year > 0
    assert result.property_depreciation_pct > 0
    assert result.total_inaction_cost_year5_chf > result.total_inaction_cost_year1_chf


@pytest.mark.asyncio
async def test_inaction_cost_depreciation_capped(db_session: AsyncSession, building_with_samples: Building):
    result = await calculate_inaction_cost(db_session, building_with_samples.id)
    assert result.property_depreciation_pct <= 30.0


@pytest.mark.asyncio
async def test_inaction_cost_pollutant_details(db_session: AsyncSession, building_with_samples: Building):
    result = await calculate_inaction_cost(db_session, building_with_samples.id)
    # Only threshold-exceeded pollutants
    types = {d.pollutant_type for d in result.pollutant_details}
    assert "asbestos" in types
    assert "pcb" in types
    assert "lead" not in types


@pytest.mark.asyncio
async def test_inaction_cost_empty_building(db_session: AsyncSession, building_no_samples: Building):
    result = await calculate_inaction_cost(db_session, building_no_samples.id)
    assert result.regulatory_fine_min_chf == 0.0
    assert result.total_inaction_cost_year1_chf == 0.0
    assert result.pollutant_details == []


@pytest.mark.asyncio
async def test_inaction_cost_not_found(db_session: AsyncSession):
    with pytest.raises(ValueError, match="not found"):
        await calculate_inaction_cost(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN4 — get_portfolio_investment_plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_plan_with_buildings(db_session: AsyncSession, org: Organization, org_user: User):
    # Create building under org user
    bldg = Building(
        id=uuid.uuid4(),
        address="Portfolio 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        surface_area_m2=400.0,
        created_by=org_user.id,
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

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="P001",
        pollutant_type="asbestos",
        risk_level="high",
        threshold_exceeded=True,
    )
    db_session.add(sample)
    await db_session.commit()

    result = await get_portfolio_investment_plan(db_session, org.id)
    assert result.organization_id == org.id
    assert len(result.ranked_buildings) == 1
    assert result.ranked_buildings[0].rank == 1
    assert result.total_portfolio_cost_chf > 0
    assert len(result.budget_breakpoints) == 3


@pytest.mark.asyncio
async def test_portfolio_plan_empty_org(db_session: AsyncSession, org: Organization):
    result = await get_portfolio_investment_plan(db_session, org.id)
    assert result.ranked_buildings == []
    assert result.total_portfolio_cost_chf == 0.0


@pytest.mark.asyncio
async def test_portfolio_plan_empty_org_random_id(db_session: AsyncSession):
    result = await get_portfolio_investment_plan(db_session, uuid.uuid4())
    assert result.total_buildings == 0


@pytest.mark.asyncio
async def test_portfolio_budget_breakpoints(db_session: AsyncSession, org: Organization, org_user: User):
    # Create a small building to fit in 100k budget
    bldg = Building(
        id=uuid.uuid4(),
        address="Small Building",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="residential",
        surface_area_m2=100.0,
        created_by=org_user.id,
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

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="BP001",
        pollutant_type="asbestos",
        risk_level="medium",
        threshold_exceeded=True,
    )
    db_session.add(sample)
    await db_session.commit()

    result = await get_portfolio_investment_plan(db_session, org.id)
    # 100m2 x 120 CHF/m2 = 12000 CHF - fits in all breakpoints
    for bp in result.budget_breakpoints:
        assert bp.buildings_covered == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_intervention_roi(client: AsyncClient, auth_headers: dict, building_with_samples: Building):
    resp = await client.get(f"/api/v1/buildings/{building_with_samples.id}/intervention-roi", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(building_with_samples.id)
    assert len(data["interventions"]) == 2


@pytest.mark.asyncio
async def test_api_intervention_roi_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/intervention-roi", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_remediation_strategies(client: AsyncClient, auth_headers: dict, building_with_samples: Building):
    resp = await client.get(
        f"/api/v1/buildings/{building_with_samples.id}/remediation-strategies", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["strategies"]) == 3


@pytest.mark.asyncio
async def test_api_inaction_cost(client: AsyncClient, auth_headers: dict, building_with_samples: Building):
    resp = await client.get(f"/api/v1/buildings/{building_with_samples.id}/inaction-cost", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["regulatory_fine_min_chf"] > 0


@pytest.mark.asyncio
async def test_api_investment_plan(client: AsyncClient, auth_headers: dict, org: Organization):
    resp = await client.get(f"/api/v1/organizations/{org.id}/investment-plan", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_investment_plan_empty_org(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/organizations/{uuid.uuid4()}/investment-plan", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] == 0


@pytest.mark.asyncio
async def test_api_no_auth(client: AsyncClient, building_with_samples: Building):
    resp = await client.get(f"/api/v1/buildings/{building_with_samples.id}/intervention-roi")
    assert resp.status_code == 403
