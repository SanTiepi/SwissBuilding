"""Tests for CAPEX planning service + API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.capex_planning_service import (
    evaluate_reserve_fund,
    forecast_investment_scenarios,
    generate_building_capex_plan,
    get_portfolio_capex_summary,
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
        name="Capex Test Org",
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
        email="capex-admin@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Capex",
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
async def empty_building(db_session, admin_user):
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2000,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def old_building_with_risk(db_session, admin_user):
    """Pre-1960 building with high-risk asbestos samples."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Vieille Rue 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1950,
        building_type="residential",
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

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_multi_pollutant(db_session, admin_user):
    """Building with multiple pollutant types."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Multi Polluant 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=bldg.id,
        diagnostic_type="full",
        status="validated",
    )
    db_session.add(diag)
    await db_session.flush()

    for pt, risk in [("asbestos", "critical"), ("pcb", "high"), ("lead", "medium")]:
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{pt[:3].upper()}",
            pollutant_type=pt,
            threshold_exceeded=True,
            risk_level=risk,
        )
        db_session.add(s)

    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_with_actions(db_session, admin_user):
    """Building with open action items but no diagnostic samples."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Action Rue 3",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1985,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    for i in range(3):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=bldg.id,
            source_type="manual",
            action_type="inspection",
            title=f"Action item {i + 1}",
            priority="high" if i == 0 else "medium",
            status="open",
        )
        db_session.add(action)

    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def org_with_buildings(db_session, org, org_admin):
    """Org with two buildings, one with pollutant issues."""
    bldg1 = Building(
        id=uuid.uuid4(),
        address="Org Bldg 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1955,
        building_type="residential",
        created_by=org_admin.id,
        status="active",
    )
    bldg2 = Building(
        id=uuid.uuid4(),
        address="Org Bldg 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2010,
        building_type="residential",
        created_by=org_admin.id,
        status="active",
    )
    db_session.add_all([bldg1, bldg2])
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=bldg1.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-ORG-01",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="critical",
    )
    db_session.add(sample)
    await db_session.commit()
    return bldg1, bldg2


# ===========================================================================
# FN1 — generate_building_capex_plan
# ===========================================================================


class TestGenerateBuildingCapexPlan:
    async def test_empty_building(self, db_session, empty_building):
        plan = await generate_building_capex_plan(empty_building.id, db_session)
        assert plan.building_id == empty_building.id
        assert plan.total_estimated == 0.0
        assert plan.line_items == []
        assert plan.planning_horizon_years == 5

    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_building_capex_plan(uuid.uuid4(), db_session)

    async def test_single_pollutant(self, db_session, old_building_with_risk):
        plan = await generate_building_capex_plan(old_building_with_risk.id, db_session)
        assert plan.total_estimated > 0
        categories = {item.category for item in plan.line_items}
        assert "diagnostic" in categories
        assert "remediation" in categories
        assert "monitoring" in categories
        assert "contingency" in categories

    async def test_multiple_pollutants(self, db_session, building_multi_pollutant):
        plan = await generate_building_capex_plan(building_multi_pollutant.id, db_session)
        pollutant_types = {item.pollutant_type for item in plan.line_items if item.pollutant_type}
        assert "asbestos" in pollutant_types
        assert "pcb" in pollutant_types
        assert "lead" in pollutant_types

    async def test_contingency_is_10_percent(self, db_session, old_building_with_risk):
        plan = await generate_building_capex_plan(old_building_with_risk.id, db_session)
        contingency_items = [i for i in plan.line_items if i.category == "contingency"]
        assert len(contingency_items) == 1
        non_contingency = sum(i.estimated_cost for i in plan.line_items if i.category != "contingency")
        expected_contingency = round(non_contingency * 0.10, 2)
        assert contingency_items[0].estimated_cost == expected_contingency

    async def test_horizon_years_affects_monitoring(self, db_session, old_building_with_risk):
        plan3 = await generate_building_capex_plan(old_building_with_risk.id, db_session, horizon_years=3)
        plan10 = await generate_building_capex_plan(old_building_with_risk.id, db_session, horizon_years=10)
        mon3 = [i for i in plan3.line_items if i.category == "monitoring"]
        mon10 = [i for i in plan10.line_items if i.category == "monitoring"]
        assert mon3[0].estimated_cost < mon10[0].estimated_cost

    async def test_action_items_included(self, db_session, building_with_actions):
        plan = await generate_building_capex_plan(building_with_actions.id, db_session)
        verification_items = [i for i in plan.line_items if i.category == "verification"]
        assert len(verification_items) == 3

    async def test_totals_by_category(self, db_session, building_multi_pollutant):
        plan = await generate_building_capex_plan(building_multi_pollutant.id, db_session)
        cat_sum = sum(plan.total_by_category.values())
        assert abs(cat_sum - plan.total_estimated) < 0.01

    async def test_totals_by_priority(self, db_session, building_multi_pollutant):
        plan = await generate_building_capex_plan(building_multi_pollutant.id, db_session)
        pri_sum = sum(plan.total_by_priority.values())
        assert abs(pri_sum - plan.total_estimated) < 0.01


# ===========================================================================
# FN2 — evaluate_reserve_fund
# ===========================================================================


class TestEvaluateReserveFund:
    async def test_new_building_adequate(self, db_session, empty_building):
        result = await evaluate_reserve_fund(empty_building.id, db_session)
        assert result.adequacy_rating == "adequate"
        assert result.recommended_annual_reserve == 0.0

    async def test_old_building_critical(self, db_session, old_building_with_risk):
        result = await evaluate_reserve_fund(old_building_with_risk.id, db_session)
        assert result.adequacy_rating == "critical"
        assert result.recommended_annual_reserve > 0

    async def test_moderate_case_insufficient(self, db_session, building_multi_pollutant):
        result = await evaluate_reserve_fund(building_multi_pollutant.id, db_session)
        assert result.adequacy_rating == "insufficient"

    async def test_current_gap_equals_reserve(self, db_session, old_building_with_risk):
        result = await evaluate_reserve_fund(old_building_with_risk.id, db_session)
        assert result.current_gap == result.recommended_annual_reserve

    async def test_breakdown_present(self, db_session, old_building_with_risk):
        result = await evaluate_reserve_fund(old_building_with_risk.id, db_session)
        assert len(result.breakdown) > 0

    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await evaluate_reserve_fund(uuid.uuid4(), db_session)


# ===========================================================================
# FN3 — forecast_investment_scenarios
# ===========================================================================


class TestForecastInvestmentScenarios:
    async def test_empty_building_scenarios(self, db_session, empty_building):
        result = await forecast_investment_scenarios(empty_building.id, db_session)
        assert len(result.scenarios) == 3
        assert result.recommended_scenario == "recommended"
        # All costs should be zero for empty building
        for s in result.scenarios:
            assert s.total_cost == 0.0

    async def test_three_scenarios_generated(self, db_session, old_building_with_risk):
        result = await forecast_investment_scenarios(old_building_with_risk.id, db_session)
        assert len(result.scenarios) == 3
        names = {s.scenario_name for s in result.scenarios}
        assert names == {"minimum_compliance", "recommended", "comprehensive"}

    async def test_recommended_flag(self, db_session, old_building_with_risk):
        result = await forecast_investment_scenarios(old_building_with_risk.id, db_session)
        recommended = [s for s in result.scenarios if s.recommended]
        assert len(recommended) == 1
        assert recommended[0].scenario_name == "recommended"

    async def test_cost_ordering(self, db_session, building_multi_pollutant):
        result = await forecast_investment_scenarios(building_multi_pollutant.id, db_session)
        costs = {s.scenario_name: s.total_cost for s in result.scenarios}
        assert costs["minimum_compliance"] <= costs["recommended"]
        assert costs["recommended"] <= costs["comprehensive"]

    async def test_risk_reduction_ordering(self, db_session, building_multi_pollutant):
        result = await forecast_investment_scenarios(building_multi_pollutant.id, db_session)
        reductions = {s.scenario_name: s.risk_reduction_pct for s in result.scenarios}
        assert reductions["minimum_compliance"] < reductions["recommended"]
        assert reductions["recommended"] < reductions["comprehensive"]

    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await forecast_investment_scenarios(uuid.uuid4(), db_session)


# ===========================================================================
# FN4 — get_portfolio_capex_summary
# ===========================================================================


class TestPortfolioCapexSummary:
    async def test_empty_org(self, db_session, org):
        result = await get_portfolio_capex_summary(org.id, db_session)
        assert result.total_buildings == 0
        assert result.total_capex_estimated == 0.0

    async def test_org_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_portfolio_capex_summary(uuid.uuid4(), db_session)

    async def test_org_with_buildings(self, db_session, org, org_with_buildings):
        result = await get_portfolio_capex_summary(org.id, db_session)
        assert result.total_buildings == 2
        assert result.total_capex_estimated > 0
        assert result.buildings_needing_urgent_investment >= 1

    async def test_aggregated_categories(self, db_session, org, org_with_buildings):
        result = await get_portfolio_capex_summary(org.id, db_session)
        assert len(result.by_category) > 0
        cat_sum = sum(result.by_category.values())
        assert abs(cat_sum - result.total_capex_estimated) < 0.01


# ===========================================================================
# API endpoint tests
# ===========================================================================


class TestCapexPlanningAPI:
    async def test_get_plan(self, client, admin_user, sample_building, auth_headers):
        resp = await client.get(
            f"/api/v1/capex-planning/buildings/{sample_building.id}/plan",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert "line_items" in data

    async def test_get_plan_with_horizon(self, client, admin_user, sample_building, auth_headers):
        resp = await client.get(
            f"/api/v1/capex-planning/buildings/{sample_building.id}/plan?horizon_years=10",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["planning_horizon_years"] == 10

    async def test_get_reserve_fund(self, client, admin_user, sample_building, auth_headers):
        resp = await client.get(
            f"/api/v1/capex-planning/buildings/{sample_building.id}/reserve-fund",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "adequacy_rating" in data

    async def test_get_investment_forecast(self, client, admin_user, sample_building, auth_headers):
        resp = await client.get(
            f"/api/v1/capex-planning/buildings/{sample_building.id}/investment-forecast",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scenarios"]) == 3

    async def test_get_portfolio_summary(self, client, db_session, admin_user, auth_headers):
        org = Organization(
            id=uuid.uuid4(),
            name="API Test Org",
            type="property_management",
        )
        db_session.add(org)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/capex-planning/organizations/{org.id}/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org.id)

    async def test_plan_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/capex-planning/buildings/{fake_id}/plan",
            headers=auth_headers,
        )
        assert resp.status_code == 404
