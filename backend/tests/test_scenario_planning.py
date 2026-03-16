"""Tests for scenario planning service and API."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.schemas.scenario_planning import InterventionConfig, ScenarioCreateRequest
from app.services.scenario_planning_service import (
    compare_scenarios,
    create_scenario,
    find_optimal_scenario,
    get_scenario_sensitivity,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_1965(db_session: AsyncSession, admin_user: User) -> Building:
    """1965 residential building in Vaud — high asbestos/PCB risk."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Scenario 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        surface_area_m2=400.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_with_diag(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with diagnostic samples confirming asbestos."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Diag 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        surface_area_m2=300.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=bldg.id,
        diagnostic_type="avant_travaux",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        location_detail="Dalle de sol",
        material_category="vinyl_tile",
        concentration=2.5,
        unit="percent_weight",
        threshold_exceeded=True,
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# Service-level tests: create_scenario
# ---------------------------------------------------------------------------


class TestCreateScenario:
    @pytest.mark.asyncio
    async def test_basic_scenario(self, db_session, building_1965):
        interventions = [
            InterventionConfig(
                intervention_type="removal",
                pollutant="asbestos",
                estimated_cost_chf=50000,
                duration_months=3,
            ),
        ]
        result = await create_scenario(db_session, building_1965.id, "Asbestos removal", interventions)
        assert result.name == "Asbestos removal"
        assert result.total_cost_chf == 50000
        assert result.overall_risk_reduction > 0

    @pytest.mark.asyncio
    async def test_empty_interventions(self, db_session, building_1965):
        result = await create_scenario(db_session, building_1965.id, "Do nothing", [])
        assert result.total_cost_chf == 0
        assert result.overall_risk_reduction == 0
        assert result.total_duration_months == 0

    @pytest.mark.asyncio
    async def test_multiple_interventions(self, db_session, building_1965):
        interventions = [
            InterventionConfig(
                intervention_type="removal",
                pollutant="asbestos",
                estimated_cost_chf=50000,
                duration_months=3,
            ),
            InterventionConfig(
                intervention_type="decontamination",
                pollutant="pcb",
                estimated_cost_chf=30000,
                duration_months=2,
            ),
        ]
        result = await create_scenario(db_session, building_1965.id, "Multi", interventions)
        assert result.total_cost_chf == 80000
        assert len(result.risk_reductions) == 5
        assert result.overall_risk_reduction > 0

    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await create_scenario(db_session, uuid.uuid4(), "X", [])

    @pytest.mark.asyncio
    async def test_compliance_impacts(self, db_session, building_1965):
        interventions = [
            InterventionConfig(
                intervention_type="removal",
                pollutant="asbestos",
                estimated_cost_chf=50000,
                duration_months=3,
            ),
        ]
        result = await create_scenario(db_session, building_1965.id, "Test", interventions)
        assert len(result.compliance_impacts) == 5
        # Asbestos should become compliant after removal
        asb = next(c for c in result.compliance_impacts if c.pollutant == "asbestos")
        assert asb.now_compliant is True

    @pytest.mark.asyncio
    async def test_with_diagnostic_data(self, db_session, building_with_diag):
        interventions = [
            InterventionConfig(
                intervention_type="removal",
                pollutant="asbestos",
                estimated_cost_chf=40000,
                duration_months=2,
            ),
        ]
        result = await create_scenario(db_session, building_with_diag.id, "Post-diag", interventions)
        # Should have higher initial risk due to confirmed asbestos
        asb = next(r for r in result.risk_reductions if r.pollutant == "asbestos")
        assert asb.before >= 0.85


# ---------------------------------------------------------------------------
# Service-level tests: compare_scenarios
# ---------------------------------------------------------------------------


class TestCompareScenarios:
    @pytest.mark.asyncio
    async def test_compare_two(self, db_session, building_1965):
        configs = [
            ScenarioCreateRequest(
                building_id=building_1965.id,
                name="Minimal",
                interventions=[
                    InterventionConfig(
                        intervention_type="encapsulation",
                        pollutant="asbestos",
                        estimated_cost_chf=10000,
                        duration_months=1,
                    ),
                ],
            ),
            ScenarioCreateRequest(
                building_id=building_1965.id,
                name="Full removal",
                interventions=[
                    InterventionConfig(
                        intervention_type="removal",
                        pollutant="asbestos",
                        estimated_cost_chf=50000,
                        duration_months=3,
                    ),
                ],
            ),
        ]
        result = await compare_scenarios(db_session, building_1965.id, configs)
        assert result.building_id == building_1965.id
        assert len(result.scenarios) == 2
        assert 0 <= result.recommended_index <= 1
        assert len(result.recommendation_reason) > 0

    @pytest.mark.asyncio
    async def test_compare_recommends_best_ratio(self, db_session, building_1965):
        configs = [
            ScenarioCreateRequest(
                building_id=building_1965.id,
                name="Cheap",
                interventions=[
                    InterventionConfig(
                        intervention_type="removal",
                        pollutant="asbestos",
                        estimated_cost_chf=1000,
                        duration_months=1,
                    ),
                ],
            ),
            ScenarioCreateRequest(
                building_id=building_1965.id,
                name="Expensive",
                interventions=[
                    InterventionConfig(
                        intervention_type="removal",
                        pollutant="asbestos",
                        estimated_cost_chf=500000,
                        duration_months=1,
                    ),
                ],
            ),
        ]
        result = await compare_scenarios(db_session, building_1965.id, configs)
        # Same risk reduction, but "Cheap" has better ratio
        assert result.recommended_index == 0

    @pytest.mark.asyncio
    async def test_compare_max_five(self, db_session, building_1965):
        configs = [
            ScenarioCreateRequest(
                building_id=building_1965.id,
                name=f"S{i}",
                interventions=[],
            )
            for i in range(6)
        ]
        with pytest.raises(ValueError, match="Maximum 5"):
            await compare_scenarios(db_session, building_1965.id, configs)


# ---------------------------------------------------------------------------
# Service-level tests: find_optimal_scenario
# ---------------------------------------------------------------------------


class TestFindOptimal:
    @pytest.mark.asyncio
    async def test_optimal_within_budget(self, db_session, building_1965):
        result = await find_optimal_scenario(db_session, building_1965.id, 200000, 12)
        assert result.budget_used_chf <= 200000
        assert result.budget_remaining_chf >= 0
        assert result.time_used_months <= 12
        assert result.scenario.overall_risk_reduction > 0

    @pytest.mark.asyncio
    async def test_optimal_tight_budget(self, db_session, building_1965):
        result = await find_optimal_scenario(db_session, building_1965.id, 100, 12)
        # Very tight budget — may select nothing
        assert result.budget_used_chf <= 100
        assert len(result.interventions_selected) == 0

    @pytest.mark.asyncio
    async def test_optimal_large_budget(self, db_session, building_1965):
        result = await find_optimal_scenario(db_session, building_1965.id, 10_000_000, 60)
        # Should select interventions for all non-compliant pollutants
        assert len(result.interventions_selected) > 0
        assert result.scenario.overall_risk_reduction > 0

    @pytest.mark.asyncio
    async def test_optimal_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await find_optimal_scenario(db_session, uuid.uuid4(), 100000, 12)

    @pytest.mark.asyncio
    async def test_optimal_time_constraint(self, db_session, building_1965):
        # Very short time limit
        result = await find_optimal_scenario(db_session, building_1965.id, 10_000_000, 0.5)
        assert result.time_used_months <= 0.5 or len(result.interventions_selected) == 0


# ---------------------------------------------------------------------------
# Service-level tests: get_scenario_sensitivity
# ---------------------------------------------------------------------------


class TestSensitivity:
    @pytest.mark.asyncio
    async def test_sensitivity_basic(self, db_session, building_1965):
        cfg = ScenarioCreateRequest(
            building_id=building_1965.id,
            name="Base",
            interventions=[
                InterventionConfig(
                    intervention_type="removal",
                    pollutant="asbestos",
                    estimated_cost_chf=50000,
                    duration_months=3,
                ),
            ],
        )
        result = await get_scenario_sensitivity(db_session, building_1965.id, cfg)
        assert result.building_id == building_1965.id
        assert result.base_scenario.name == "Base"
        assert result.cost_plus_20.total_cost_chf > result.base_scenario.total_cost_chf
        assert result.cost_minus_20.total_cost_chf < result.base_scenario.total_cost_chf
        assert 0.0 <= result.robustness_score <= 1.0

    @pytest.mark.asyncio
    async def test_sensitivity_removal_variants(self, db_session, building_1965):
        cfg = ScenarioCreateRequest(
            building_id=building_1965.id,
            name="Multi",
            interventions=[
                InterventionConfig(
                    intervention_type="removal",
                    pollutant="asbestos",
                    estimated_cost_chf=50000,
                    duration_months=3,
                ),
                InterventionConfig(
                    intervention_type="decontamination",
                    pollutant="pcb",
                    estimated_cost_chf=30000,
                    duration_months=2,
                ),
            ],
        )
        result = await get_scenario_sensitivity(db_session, building_1965.id, cfg)
        assert len(result.removal_variants) == 2
        # Each removal variant should have lower risk reduction
        for rv in result.removal_variants:
            assert rv.overall_risk_reduction < result.base_scenario.overall_risk_reduction

    @pytest.mark.asyncio
    async def test_sensitivity_empty_scenario(self, db_session, building_1965):
        cfg = ScenarioCreateRequest(
            building_id=building_1965.id,
            name="Empty",
            interventions=[],
        )
        result = await get_scenario_sensitivity(db_session, building_1965.id, cfg)
        # Empty scenario: all variants identical → robustness depends on
        # zero-division guard (base_rr=0.001, all_rrs all 0.0)
        assert 0.0 <= result.robustness_score <= 1.0
        assert len(result.removal_variants) == 0


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestScenarioAPI:
    @pytest.mark.asyncio
    async def test_create_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/scenarios",
            json={
                "building_id": str(sample_building.id),
                "name": "API test",
                "interventions": [
                    {
                        "intervention_type": "removal",
                        "pollutant": "asbestos",
                        "estimated_cost_chf": 40000,
                        "duration_months": 2,
                    }
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "API test"
        assert data["total_cost_chf"] == 40000

    @pytest.mark.asyncio
    async def test_compare_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/scenarios/compare",
            json={
                "building_id": str(sample_building.id),
                "scenarios": [
                    {
                        "building_id": str(sample_building.id),
                        "name": "A",
                        "interventions": [
                            {
                                "intervention_type": "removal",
                                "pollutant": "asbestos",
                                "estimated_cost_chf": 50000,
                                "duration_months": 3,
                            }
                        ],
                    },
                    {
                        "building_id": str(sample_building.id),
                        "name": "B",
                        "interventions": [
                            {
                                "intervention_type": "encapsulation",
                                "pollutant": "asbestos",
                                "estimated_cost_chf": 10000,
                                "duration_months": 1,
                            }
                        ],
                    },
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scenarios"]) == 2
        assert "recommended_index" in data

    @pytest.mark.asyncio
    async def test_optimal_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/scenarios/optimal",
            json={
                "building_id": str(sample_building.id),
                "budget_limit_chf": 200000,
                "time_limit_months": 12,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["budget_used_chf"] <= 200000
        assert "scenario" in data

    @pytest.mark.asyncio
    async def test_sensitivity_endpoint(self, client: AsyncClient, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/scenarios/sensitivity",
            json={
                "building_id": str(sample_building.id),
                "scenario": {
                    "building_id": str(sample_building.id),
                    "name": "Sens",
                    "interventions": [
                        {
                            "intervention_type": "removal",
                            "pollutant": "asbestos",
                            "estimated_cost_chf": 50000,
                            "duration_months": 3,
                        }
                    ],
                },
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "robustness_score" in data

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client: AsyncClient, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/scenarios",
            json={
                "building_id": str(sample_building.id),
                "name": "No auth",
                "interventions": [],
            },
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_building_not_found_api(self, client: AsyncClient, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/buildings/{fake_id}/scenarios",
            json={
                "building_id": fake_id,
                "name": "Missing",
                "interventions": [],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
