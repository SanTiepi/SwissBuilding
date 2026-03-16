"""Tests for counterfactual analysis service and API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.counterfactual_analysis_service import (
    analyze_timeline_alternatives,
    run_counterfactual,
    run_portfolio_stress_test,
    run_stress_test,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_user_with_org(db: AsyncSession, org: Organization) -> User:
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="Member",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_building_for_user(db: AsyncSession, user: User) -> Building:
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
        surface_area_m2=300.0,
    )
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


async def _create_diagnostic_with_samples(
    db: AsyncSession, building: Building, admin_user: User
) -> tuple[Diagnostic, list[Sample]]:
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db.add(diag)
    await db.commit()
    await db.refresh(diag)

    samples = []
    for i, (pt, conc, exceeded, rl) in enumerate(
        [
            ("asbestos", 5000.0, True, "high"),
            ("pcb", 80.0, True, "medium"),
            ("lead", 100.0, False, "low"),
        ]
    ):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{i + 1}",
            pollutant_type=pt,
            concentration=conc,
            threshold_exceeded=exceeded,
            risk_level=rl,
            location_detail=f"Room {i + 1}",
        )
        db.add(s)
        samples.append(s)

    await db.commit()
    for s in samples:
        await db.refresh(s)
    return diag, samples


# ---------------------------------------------------------------------------
# FN1 — run_counterfactual
# ---------------------------------------------------------------------------


class TestRunCounterfactual:
    @pytest.mark.asyncio
    async def test_delayed_action(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_counterfactual(sample_building.id, "delayed_action", db_session)

        assert result.building_id == sample_building.id
        assert result.scenario.scenario_type == "delayed_action"
        assert result.overall_impact == "negative"
        assert result.cost_impact_chf > 0
        assert len(result.impacts) == 3
        cost_metric = next(m for m in result.impacts if m.metric_name == "remediation_cost")
        assert cost_metric.direction == "worse"
        assert cost_metric.delta_pct == 30.0

    @pytest.mark.asyncio
    async def test_early_intervention(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_counterfactual(sample_building.id, "early_intervention", db_session)

        assert result.overall_impact == "positive"
        assert result.cost_impact_chf < 0
        cost_metric = next(m for m in result.impacts if m.metric_name == "remediation_cost")
        assert cost_metric.direction == "better"

    @pytest.mark.asyncio
    async def test_regulation_change(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_counterfactual(sample_building.id, "regulation_change", db_session)

        assert result.overall_impact == "negative"
        assert result.scenario.scenario_type == "regulation_change"
        assert len(result.impacts) >= 2

    @pytest.mark.asyncio
    async def test_budget_cut(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_counterfactual(sample_building.id, "budget_cut", db_session)

        assert result.overall_impact == "negative"
        assert result.scenario.scenario_type == "budget_cut"

    @pytest.mark.asyncio
    async def test_natural_event_fallback(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_counterfactual(sample_building.id, "natural_event", db_session)

        assert result.overall_impact == "negative"
        assert result.scenario.scenario_type == "natural_event"

    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await run_counterfactual(uuid.uuid4(), "delayed_action", db_session)

    @pytest.mark.asyncio
    async def test_no_samples(self, db_session, sample_building):
        result = await run_counterfactual(sample_building.id, "delayed_action", db_session)
        assert result.building_id == sample_building.id
        assert result.cost_impact_chf == 0.0


# ---------------------------------------------------------------------------
# FN2 — run_stress_test
# ---------------------------------------------------------------------------


class TestRunStressTest:
    @pytest.mark.asyncio
    async def test_regulatory_tightening(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_stress_test(sample_building.id, "regulatory_tightening", db_session)

        assert result.building_id == sample_building.id
        assert result.stress_type == "regulatory_tightening"
        assert 0.0 <= result.resilience_score <= 1.0
        assert len(result.parameters) >= 1
        assert result.parameters[0].parameter_name == "threshold_factor"

    @pytest.mark.asyncio
    async def test_cost_increase(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_stress_test(sample_building.id, "cost_increase", db_session)

        assert result.stress_type == "cost_increase"
        assert result.additional_cost > 0

    @pytest.mark.asyncio
    async def test_timeline_acceleration(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_stress_test(sample_building.id, "timeline_acceleration", db_session)

        assert result.stress_type == "timeline_acceleration"
        assert result.additional_cost > 0

    @pytest.mark.asyncio
    async def test_resource_scarcity(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await run_stress_test(sample_building.id, "resource_scarcity", db_session)

        assert result.stress_type == "resource_scarcity"
        assert result.resilience_score == 0.75

    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await run_stress_test(uuid.uuid4(), "regulatory_tightening", db_session)

    @pytest.mark.asyncio
    async def test_unknown_stress_type(self, db_session, sample_building):
        result = await run_stress_test(sample_building.id, "unknown_type", db_session)
        assert result.stress_type == "unknown_type"
        assert result.resilience_score == 0.5


# ---------------------------------------------------------------------------
# FN3 — analyze_timeline_alternatives
# ---------------------------------------------------------------------------


class TestTimelineAlternatives:
    @pytest.mark.asyncio
    async def test_generates_three_alternatives(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await analyze_timeline_alternatives(sample_building.id, db_session)

        assert result.building_id == sample_building.id
        assert len(result.alternatives) == 3
        ids = {a.alternative_id for a in result.alternatives}
        assert ids == {"accelerated", "standard", "extended"}

    @pytest.mark.asyncio
    async def test_one_is_optimal(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await analyze_timeline_alternatives(sample_building.id, db_session)

        optimal = [a for a in result.alternatives if a.is_optimal]
        assert len(optimal) == 1

    @pytest.mark.asyncio
    async def test_risk_reduction_ordering(self, db_session, admin_user, sample_building):
        await _create_diagnostic_with_samples(db_session, sample_building, admin_user)
        result = await analyze_timeline_alternatives(sample_building.id, db_session)

        accel = next(a for a in result.alternatives if a.alternative_id == "accelerated")
        standard = next(a for a in result.alternatives if a.alternative_id == "standard")
        extended = next(a for a in result.alternatives if a.alternative_id == "extended")
        assert accel.risk_reduction_pct > standard.risk_reduction_pct > extended.risk_reduction_pct

    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await analyze_timeline_alternatives(uuid.uuid4(), db_session)


# ---------------------------------------------------------------------------
# FN4 — run_portfolio_stress_test
# ---------------------------------------------------------------------------


class TestPortfolioStressTest:
    @pytest.mark.asyncio
    async def test_with_buildings(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user_with_org(db_session, org)
        await _create_building_for_user(db_session, user)
        await _create_building_for_user(db_session, user)

        result = await run_portfolio_stress_test(org.id, "regulatory_tightening", db_session)

        assert result.organization_id == org.id
        assert result.total_buildings_tested == 2
        assert result.buildings_resilient + result.buildings_at_risk == 2
        assert 0.0 <= result.average_resilience_score <= 1.0

    @pytest.mark.asyncio
    async def test_empty_org(self, db_session):
        org = await _create_org(db_session)

        result = await run_portfolio_stress_test(org.id, "cost_increase", db_session)

        assert result.total_buildings_tested == 0
        assert result.average_resilience_score == 0.0

    @pytest.mark.asyncio
    async def test_org_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await run_portfolio_stress_test(uuid.uuid4(), "cost_increase", db_session)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestCounterfactualAPI:
    @pytest.mark.asyncio
    async def test_scenario_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/counterfactual-analysis/buildings/{sample_building.id}/scenario",
            params={"scenario_type": "delayed_action"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert data["scenario"]["scenario_type"] == "delayed_action"

    @pytest.mark.asyncio
    async def test_scenario_endpoint_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            f"/api/v1/counterfactual-analysis/buildings/{uuid.uuid4()}/scenario",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stress_test_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/counterfactual-analysis/buildings/{sample_building.id}/stress-test",
            params={"stress_type": "cost_increase"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stress_type"] == "cost_increase"

    @pytest.mark.asyncio
    async def test_timeline_alternatives_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/counterfactual-analysis/buildings/{sample_building.id}/timeline-alternatives",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["alternatives"]) == 3

    @pytest.mark.asyncio
    async def test_portfolio_stress_test_endpoint(self, client: AsyncClient, auth_headers, db_session):
        org = await _create_org(db_session)
        resp = await client.get(
            f"/api/v1/counterfactual-analysis/organizations/{org.id}/stress-test",
            params={"stress_type": "regulatory_tightening"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org.id)

    @pytest.mark.asyncio
    async def test_portfolio_stress_test_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            f"/api/v1/counterfactual-analysis/organizations/{uuid.uuid4()}/stress-test",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client: AsyncClient, sample_building):
        resp = await client.get(
            f"/api/v1/counterfactual-analysis/buildings/{sample_building.id}/scenario",
        )
        assert resp.status_code in (401, 403)
