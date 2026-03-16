"""Tests for the Portfolio Optimization Service."""

from __future__ import annotations

import uuid

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.services.portfolio_optimization_service import (
    _combined_score,
    _compute_impact_score,
    _compute_risk_score,
    _compute_roi_score,
    _compute_urgency_score,
    _construction_year_risk,
    analyze_portfolio_risk_distribution,
    get_portfolio_action_plan,
    prioritize_buildings,
    simulate_budget_allocation,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "surface_area_m2": 500.0,
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_action(db, building_id, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": "diagnostic",
        "action_type": "remediation",
        "title": "Remove asbestos",
        "priority": "high",
        "status": "open",
        "created_by": admin_user.id,
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.flush()
    return a


# ── Unit tests for scoring functions ──────────────────────────────


class TestConstructionYearRisk:
    def test_none_year(self):
        assert _construction_year_risk(None) == 50.0

    def test_pre_1920(self):
        assert _construction_year_risk(1910) == 30.0

    def test_peak_risk_1970s(self):
        assert _construction_year_risk(1975) == 90.0

    def test_modern_low_risk(self):
        assert _construction_year_risk(2010) == 10.0


class TestRiskScore:
    def test_no_diagnostics(self):
        score = _compute_risk_score(0, [], 2020)
        assert 0 <= score <= 100

    def test_asbestos_1975(self):
        score = _compute_risk_score(2, ["asbestos"], 1975)
        assert score > 40  # high year risk + asbestos

    def test_multiple_pollutants_increases_risk(self):
        single = _compute_risk_score(1, ["asbestos"], 1975)
        multi = _compute_risk_score(1, ["asbestos", "pcb", "lead"], 1975)
        assert multi > single

    def test_score_capped_at_100(self):
        score = _compute_risk_score(20, ["asbestos", "pcb", "lead", "hap", "radon"], 1975)
        assert score <= 100.0


class TestUrgencyScore:
    def test_no_actions(self):
        assert _compute_urgency_score(0, 0, 0) == 0.0

    def test_pending_actions(self):
        score = _compute_urgency_score(5, 0, 0)
        assert score > 0

    def test_overdue_increases_urgency(self):
        no_overdue = _compute_urgency_score(3, 0, 0)
        with_overdue = _compute_urgency_score(3, 2, 0)
        assert with_overdue > no_overdue

    def test_critical_increases_urgency(self):
        no_crit = _compute_urgency_score(3, 0, 0)
        with_crit = _compute_urgency_score(3, 0, 2)
        assert with_crit > no_crit

    def test_score_capped_at_100(self):
        score = _compute_urgency_score(20, 20, 20)
        assert score <= 100.0


class TestImpactScore:
    def test_residential_higher_than_commercial(self):
        res = _compute_impact_score(500, "residential")
        com = _compute_impact_score(500, "commercial")
        assert res > com

    def test_larger_surface_higher_impact(self):
        small = _compute_impact_score(100, "residential")
        large = _compute_impact_score(2000, "residential")
        assert large > small

    def test_none_surface(self):
        score = _compute_impact_score(None, "residential")
        assert 0 <= score <= 100

    def test_score_capped_at_100(self):
        score = _compute_impact_score(100_000, "residential")
        assert score <= 100.0


class TestROIScore:
    def test_zero_cost(self):
        assert _compute_roi_score(50.0, 0.0) == 0.0

    def test_higher_risk_better_roi(self):
        low = _compute_roi_score(20.0, 30_000.0)
        high = _compute_roi_score(80.0, 30_000.0)
        assert high > low


class TestCombinedScore:
    def test_weighting(self):
        score = _combined_score(100.0, 100.0, 100.0, 100.0)
        assert score == 100.0

    def test_risk_weight_highest(self):
        # Risk has 0.4 weight, so boosting risk should increase total more
        risk_heavy = _combined_score(100.0, 0.0, 0.0, 0.0)
        urgency_heavy = _combined_score(0.0, 100.0, 0.0, 0.0)
        assert risk_heavy > urgency_heavy

    def test_roi_weight_lowest(self):
        roi_only = _combined_score(0.0, 0.0, 0.0, 100.0)
        assert roi_only == 10.0  # 0.1 * 100


# ── Integration tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prioritize_empty_portfolio(db_session):
    result = await prioritize_buildings(db_session)
    assert result.total_buildings == 0
    assert result.prioritized_buildings == []
    assert result.total_estimated_cost_chf == 0.0


@pytest.mark.asyncio
async def test_prioritize_single_building(db_session, admin_user):
    b = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, b.id, diagnostic_type="asbestos")
    await db_session.commit()

    result = await prioritize_buildings(db_session)
    assert result.total_buildings == 1
    assert result.prioritized_buildings[0].rank == 1
    assert result.prioritized_buildings[0].risk_score > 0


@pytest.mark.asyncio
async def test_prioritize_multi_building_ranking(db_session, admin_user):
    """High-risk building should rank above low-risk."""
    high_risk = await _create_building(db_session, admin_user, address="High Risk", construction_year=1975)
    await _create_diagnostic(db_session, high_risk.id, diagnostic_type="asbestos")
    await _create_diagnostic(db_session, high_risk.id, diagnostic_type="pcb")
    await _create_action(db_session, high_risk.id, admin_user, priority="critical")

    await _create_building(db_session, admin_user, address="Low Risk", construction_year=2015)
    await db_session.commit()

    result = await prioritize_buildings(db_session)
    assert result.total_buildings == 2
    assert result.prioritized_buildings[0].address == "High Risk"
    assert result.prioritized_buildings[1].address == "Low Risk"
    assert result.prioritized_buildings[0].combined_score > result.prioritized_buildings[1].combined_score


@pytest.mark.asyncio
async def test_prioritize_with_budget(db_session, admin_user):
    b = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, b.id)
    await db_session.commit()

    result = await prioritize_buildings(db_session, budget_chf=100_000.0)
    assert result.budget_chf == 100_000.0
    assert result.budget_coverage_percent is not None
    assert result.prioritized_buildings[0].recommended_budget_chf is not None


@pytest.mark.asyncio
async def test_prioritize_budget_constraint_partial(db_session, admin_user):
    """Small budget = partial coverage."""
    b = await _create_building(db_session, admin_user)
    await _create_action(db_session, b.id, admin_user, priority="critical")
    await _create_action(db_session, b.id, admin_user, priority="high", title="Action 2")
    await db_session.commit()

    result = await prioritize_buildings(db_session, budget_chf=1_000.0)
    assert result.budget_coverage_percent is not None
    assert result.budget_coverage_percent < 100.0


@pytest.mark.asyncio
async def test_portfolio_no_diagnostics_low_risk(db_session, admin_user):
    """Building with no diagnostics should have lower risk score."""
    await _create_building(db_session, admin_user, construction_year=2020)
    await db_session.commit()

    result = await prioritize_buildings(db_session)
    assert result.prioritized_buildings[0].risk_score < 30


@pytest.mark.asyncio
async def test_action_plan_generation(db_session, admin_user):
    b = await _create_building(db_session, admin_user)
    await _create_action(db_session, b.id, admin_user, title="Remove asbestos panels")
    await db_session.commit()

    result = await get_portfolio_action_plan(db_session, max_buildings=5)
    assert result.total_buildings_analyzed == 1
    assert len(result.action_plan) == 1
    assert "Remove asbestos panels" in result.action_plan[0].recommended_actions
    assert result.total_estimated_cost_chf > 0


@pytest.mark.asyncio
async def test_action_plan_top_n(db_session, admin_user):
    """Only top N buildings should appear."""
    for i in range(5):
        await _create_building(db_session, admin_user, address=f"Building {i}")
    await db_session.commit()

    result = await get_portfolio_action_plan(db_session, max_buildings=3)
    assert result.total_buildings_analyzed == 3


@pytest.mark.asyncio
async def test_action_plan_empty(db_session):
    result = await get_portfolio_action_plan(db_session)
    assert result.total_buildings_analyzed == 0
    assert result.action_plan == []


@pytest.mark.asyncio
async def test_risk_distribution_by_canton(db_session, admin_user):
    await _create_building(db_session, admin_user, canton="VD")
    await _create_building(db_session, admin_user, canton="GE", address="Rue GE 1")
    await db_session.commit()

    result = await analyze_portfolio_risk_distribution(db_session)
    assert "VD" in result.by_canton
    assert "GE" in result.by_canton


@pytest.mark.asyncio
async def test_risk_distribution_by_building_type(db_session, admin_user):
    await _create_building(db_session, admin_user, building_type="residential")
    await _create_building(db_session, admin_user, building_type="commercial", address="Commercial 1")
    await db_session.commit()

    result = await analyze_portfolio_risk_distribution(db_session)
    assert "residential" in result.by_building_type
    assert "commercial" in result.by_building_type


@pytest.mark.asyncio
async def test_risk_distribution_by_decade(db_session, admin_user):
    await _create_building(db_session, admin_user, construction_year=1975)
    await _create_building(db_session, admin_user, construction_year=2010, address="Modern 1")
    await db_session.commit()

    result = await analyze_portfolio_risk_distribution(db_session)
    assert "1970s" in result.by_decade
    assert "2010s" in result.by_decade


@pytest.mark.asyncio
async def test_risk_distribution_by_pollutant(db_session, admin_user):
    b = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, b.id, diagnostic_type="asbestos")
    await _create_diagnostic(db_session, b.id, diagnostic_type="pcb")
    await db_session.commit()

    result = await analyze_portfolio_risk_distribution(db_session)
    assert "asbestos" in result.by_pollutant
    assert "pcb" in result.by_pollutant


@pytest.mark.asyncio
async def test_risk_distribution_empty(db_session):
    result = await analyze_portfolio_risk_distribution(db_session)
    assert result.by_canton == {}
    assert result.highest_risk_cluster == "none"


@pytest.mark.asyncio
async def test_budget_simulation_three_buildings(db_session, admin_user):
    buildings = []
    for i in range(3):
        b = await _create_building(
            db_session,
            admin_user,
            address=f"Sim Building {i}",
            construction_year=1970 + i * 20,
        )
        await _create_diagnostic(db_session, b.id)
        buildings.append(b)
    await db_session.commit()

    result = await simulate_budget_allocation(
        db_session,
        building_ids=[b.id for b in buildings],
        total_budget_chf=100_000.0,
    )
    assert result.total_budget_chf == 100_000.0
    assert len(result.allocations) == 3
    total_allocated = sum(a.allocated_chf for a in result.allocations)
    assert total_allocated <= 100_000.0
    assert result.expected_portfolio_risk_reduction > 0


@pytest.mark.asyncio
async def test_high_risk_building_gets_more_budget(db_session, admin_user):
    high = await _create_building(db_session, admin_user, address="High", construction_year=1975)
    await _create_diagnostic(db_session, high.id, diagnostic_type="asbestos")
    await _create_diagnostic(db_session, high.id, diagnostic_type="pcb")
    await _create_action(db_session, high.id, admin_user, priority="critical")

    low = await _create_building(db_session, admin_user, address="Low", construction_year=2020)
    await db_session.commit()

    result = await simulate_budget_allocation(
        db_session,
        building_ids=[high.id, low.id],
        total_budget_chf=50_000.0,
    )
    alloc_map = {str(a.building_id): a for a in result.allocations}
    assert alloc_map[str(high.id)].allocated_chf > alloc_map[str(low.id)].allocated_chf


@pytest.mark.asyncio
async def test_budget_simulation_empty(db_session):
    result = await simulate_budget_allocation(db_session, building_ids=[], total_budget_chf=10_000.0)
    assert len(result.allocations) == 0
    assert result.unallocated_chf == 10_000.0


@pytest.mark.asyncio
async def test_combined_score_weighting_integration(db_session, admin_user):
    """Verify the 0.4/0.3/0.2/0.1 weighting through the full pipeline."""
    b = await _create_building(db_session, admin_user, construction_year=1975, surface_area_m2=1000.0)
    await _create_diagnostic(db_session, b.id, diagnostic_type="asbestos")
    await _create_action(db_session, b.id, admin_user, priority="critical", status="open")
    await db_session.commit()

    result = await prioritize_buildings(db_session)
    bp = result.prioritized_buildings[0]
    expected = round(
        0.4 * bp.risk_score + 0.3 * bp.urgency_score + 0.2 * bp.impact_score + 0.1 * bp.roi_score,
        2,
    )
    assert abs(bp.combined_score - expected) < 0.1
