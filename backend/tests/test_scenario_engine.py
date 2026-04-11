"""Tests for counterfactual scenario engine — model, service, API."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.organization import Organization
from app.models.scenario import SCENARIO_STATUSES, SCENARIO_TYPES
from app.models.user import User
from app.services.scenario_engine import (
    compare_scenarios,
    create_scenario,
    evaluate_scenario,
    generate_standard_scenarios,
    get_building_scenarios,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(id=uuid.uuid4(), name="Scenario Test Org", type="property_management")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def scenario_building(db_session: AsyncSession, admin_user: User) -> Building:
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Contrefactuel 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        surface_area_m2=400.0,
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------


class TestScenarioConstants:
    def test_scenario_types(self):
        assert "do_nothing" in SCENARIO_TYPES
        assert "postpone" in SCENARIO_TYPES
        assert "phase" in SCENARIO_TYPES
        assert "sell_before_works" in SCENARIO_TYPES
        assert "sell_after_works" in SCENARIO_TYPES
        assert "insure_before" in SCENARIO_TYPES
        assert "insure_after" in SCENARIO_TYPES
        assert "funding_timing" in SCENARIO_TYPES
        assert "alternative_approach" in SCENARIO_TYPES
        assert len(SCENARIO_TYPES) == 12

    def test_scenario_statuses(self):
        assert "draft" in SCENARIO_STATUSES
        assert "evaluated" in SCENARIO_STATUSES
        assert "compared" in SCENARIO_STATUSES
        assert "archived" in SCENARIO_STATUSES


# ---------------------------------------------------------------------------
# Service: create_scenario
# ---------------------------------------------------------------------------


class TestCreateScenario:
    async def test_create_do_nothing(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="do_nothing",
            title="Ne rien faire",
            assumptions={"delay_months": 12},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        assert s.id is not None
        assert s.scenario_type == "do_nothing"
        assert s.title == "Ne rien faire"
        assert s.status == "draft"
        assert s.assumptions == {"delay_months": 12}

    async def test_create_with_case_id(self, db_session, scenario_building, admin_user, org):
        fake_case_id = None  # case_id is nullable
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="phase",
            title="Phasage",
            assumptions={"phase_count": 3},
            created_by_id=admin_user.id,
            org_id=org.id,
            case_id=fake_case_id,
        )
        assert s.case_id is None
        assert s.scenario_type == "phase"

    async def test_create_invalid_type(self, db_session, scenario_building, admin_user, org):
        with pytest.raises(ValueError, match="Unknown scenario_type"):
            await create_scenario(
                db_session,
                building_id=scenario_building.id,
                scenario_type="invalid_type",
                title="Bad",
                assumptions={},
                created_by_id=admin_user.id,
                org_id=org.id,
            )

    async def test_create_invalid_building(self, db_session, admin_user, org):
        with pytest.raises(ValueError, match="not found"):
            await create_scenario(
                db_session,
                building_id=uuid.uuid4(),
                scenario_type="do_nothing",
                title="Bad",
                assumptions={},
                created_by_id=admin_user.id,
                org_id=org.id,
            )


# ---------------------------------------------------------------------------
# Service: evaluate_scenario
# ---------------------------------------------------------------------------


class TestEvaluateScenario:
    async def test_evaluate_do_nothing(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="do_nothing",
            title="Ne rien faire 1 an",
            assumptions={"delay_months": 12},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, summary = await evaluate_scenario(db_session, s.id)
        assert scenario.status == "evaluated"
        assert scenario.projected_grade is not None
        assert scenario.projected_cost_chf == 0.0
        assert scenario.projected_timeline_months == 12
        assert scenario.advantages is not None
        assert len(scenario.advantages) > 0
        assert scenario.disadvantages is not None
        assert len(scenario.disadvantages) > 0
        assert "evalue" in summary.lower()

    async def test_evaluate_postpone(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="postpone",
            title="Reporter 6 mois",
            assumptions={"delay_months": 6},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.status == "evaluated"
        assert scenario.projected_cost_chf is not None
        assert scenario.projected_cost_chf > 0
        assert scenario.baseline_cost_chf is not None

    async def test_evaluate_sell_before_works(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="sell_before_works",
            title="Vendre avant travaux",
            assumptions={"action": "sell", "timing": "before_works"},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.projected_cost_chf == 0.0
        assert scenario.risk_tradeoffs is not None
        assert len(scenario.risk_tradeoffs) > 0

    async def test_evaluate_sell_after_works(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="sell_after_works",
            title="Vendre apres travaux",
            assumptions={"action": "sell", "timing": "after_works"},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.projected_cost_chf > 0
        assert scenario.projected_grade is not None

    async def test_evaluate_phase(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="phase",
            title="Phasage 2 ans",
            assumptions={"phase_count": 3, "total_months": 24},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.projected_timeline_months == 24

    async def test_evaluate_insure_before(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="insure_before",
            title="Assurer avant travaux",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.projected_cost_chf == 0.0

    async def test_evaluate_funding_timing(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="funding_timing",
            title="Avec subvention",
            assumptions={"funding_scenario": "with_subsidy"},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.projected_cost_chf is not None
        # Funding scenario should reduce cost
        assert scenario.projected_cost_chf < scenario.baseline_cost_chf

    async def test_evaluate_widen_scope(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="widen_scope",
            title="Elargir le perimetre",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.projected_cost_chf > scenario.baseline_cost_chf

    async def test_evaluate_reduce_scope(self, db_session, scenario_building, admin_user, org):
        s = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="reduce_scope",
            title="Reduire le perimetre",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        scenario, _ = await evaluate_scenario(db_session, s.id)
        assert scenario.projected_cost_chf < scenario.baseline_cost_chf

    async def test_evaluate_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await evaluate_scenario(db_session, uuid.uuid4())

    async def test_evaluate_all_types(self, db_session, scenario_building, admin_user, org):
        """Every scenario type can be created and evaluated without error."""
        for stype in SCENARIO_TYPES:
            s = await create_scenario(
                db_session,
                building_id=scenario_building.id,
                scenario_type=stype,
                title=f"Test {stype}",
                assumptions={"delay_months": 6},
                created_by_id=admin_user.id,
                org_id=org.id,
            )
            scenario, summary = await evaluate_scenario(db_session, s.id)
            assert scenario.status == "evaluated"
            assert scenario.projected_grade is not None
            assert summary is not None


# ---------------------------------------------------------------------------
# Service: compare_scenarios
# ---------------------------------------------------------------------------


class TestCompareScenarios:
    async def test_compare_two(self, db_session, scenario_building, admin_user, org):
        s1 = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="do_nothing",
            title="Ne rien faire",
            assumptions={"delay_months": 12},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        s2 = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="sell_after_works",
            title="Vendre apres travaux",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        # Evaluate both first
        await evaluate_scenario(db_session, s1.id)
        await evaluate_scenario(db_session, s2.id)

        result = await compare_scenarios(db_session, scenario_building.id, [s1.id, s2.id])
        assert result["building_id"] == str(scenario_building.id)
        assert len(result["scenarios"]) == 2
        assert result["recommendation"] is not None

    async def test_compare_too_few(self, db_session, scenario_building, admin_user, org):
        s1 = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="do_nothing",
            title="Seul",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        with pytest.raises(ValueError, match="At least 2"):
            await compare_scenarios(db_session, scenario_building.id, [s1.id])

    async def test_compare_missing_scenario(self, db_session, scenario_building, admin_user, org):
        s1 = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="do_nothing",
            title="Existe",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        with pytest.raises(ValueError, match="not found"):
            await compare_scenarios(db_session, scenario_building.id, [s1.id, uuid.uuid4()])


# ---------------------------------------------------------------------------
# Service: generate_standard_scenarios
# ---------------------------------------------------------------------------


class TestGenerateStandardScenarios:
    async def test_generates_six(self, db_session, scenario_building, admin_user, org):
        scenarios = await generate_standard_scenarios(
            db_session,
            building_id=scenario_building.id,
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        assert len(scenarios) == 6
        types = [s.scenario_type for s in scenarios]
        assert "do_nothing" in types
        assert "phase" in types
        assert "sell_before_works" in types
        assert "sell_after_works" in types
        assert "alternative_approach" in types

    async def test_all_start_as_draft(self, db_session, scenario_building, admin_user, org):
        scenarios = await generate_standard_scenarios(
            db_session,
            building_id=scenario_building.id,
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        for s in scenarios:
            assert s.status == "draft"

    async def test_invalid_building(self, db_session, admin_user, org):
        with pytest.raises(ValueError, match="not found"):
            await generate_standard_scenarios(
                db_session,
                building_id=uuid.uuid4(),
                created_by_id=admin_user.id,
                org_id=org.id,
            )


# ---------------------------------------------------------------------------
# Service: get_building_scenarios
# ---------------------------------------------------------------------------


class TestGetBuildingScenarios:
    async def test_list_all(self, db_session, scenario_building, admin_user, org):
        await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="do_nothing",
            title="S1",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="phase",
            title="S2",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        result = await get_building_scenarios(db_session, scenario_building.id)
        assert len(result) == 2

    async def test_list_by_status(self, db_session, scenario_building, admin_user, org):
        s1 = await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="do_nothing",
            title="S1",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )
        await evaluate_scenario(db_session, s1.id)

        await create_scenario(
            db_session,
            building_id=scenario_building.id,
            scenario_type="phase",
            title="S2",
            assumptions={},
            created_by_id=admin_user.id,
            org_id=org.id,
        )

        drafts = await get_building_scenarios(db_session, scenario_building.id, status="draft")
        assert len(drafts) == 1
        assert drafts[0].title == "S2"

        evaluated = await get_building_scenarios(db_session, scenario_building.id, status="evaluated")
        assert len(evaluated) == 1
        assert evaluated[0].title == "S1"

    async def test_empty_building(self, db_session, scenario_building):
        result = await get_building_scenarios(db_session, scenario_building.id)
        assert result == []
