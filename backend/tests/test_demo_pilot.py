"""BatiConnect — Tests for Demo Scenario, Pilot Scorecard, ROI Calculator, and Case Study Template."""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.api.demo_pilot import router as demo_pilot_router
from app.main import app
from app.models.case_study_template import CaseStudyTemplate
from app.models.demo_scenario import DemoRunbookStep, DemoScenario
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.pilot_scorecard import PilotMetric, PilotScorecard
from app.schemas.demo_pilot import (
    CaseStudyTemplateRead,
    DemoScenarioRead,
    PilotMetricRead,
    PilotScorecardWithMetrics,
)
from app.schemas.roi import ROIBreakdown, ROIReport
from app.services.roi_calculator_service import calculate_building_roi

# Register routes for HTTP tests
app.include_router(demo_pilot_router, prefix="/api/v1")


# ---- Model Tests ----


@pytest.mark.asyncio
async def test_create_demo_scenario(db_session):
    scenario = DemoScenario(
        id=uuid.uuid4(),
        scenario_code="test-scenario-001",
        title="Test Scenario",
        persona_target="property_manager",
        starting_state_description="A test starting state.",
        reveal_surfaces=["ControlTower", "PassportCard"],
        proof_moment="Test proof moment",
        is_active=True,
    )
    db_session.add(scenario)
    await db_session.flush()
    assert scenario.id is not None
    assert scenario.scenario_code == "test-scenario-001"


@pytest.mark.asyncio
async def test_create_demo_runbook_step(db_session):
    scenario = DemoScenario(
        id=uuid.uuid4(),
        scenario_code="test-runbook-scenario",
        title="Runbook Test",
        persona_target="owner",
        starting_state_description="Start.",
        reveal_surfaces=["PassportCard"],
        is_active=True,
    )
    db_session.add(scenario)
    await db_session.flush()

    step = DemoRunbookStep(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        step_order=1,
        title="Step One",
        description="First step description.",
        expected_ui_state="Dashboard visible",
    )
    db_session.add(step)
    await db_session.flush()
    assert step.scenario_id == scenario.id
    assert step.step_order == 1


@pytest.mark.asyncio
async def test_create_pilot_scorecard(db_session):
    scorecard = PilotScorecard(
        id=uuid.uuid4(),
        pilot_name="Test Pilot",
        pilot_code="test-pilot-001",
        status="active",
        start_date=date(2026, 4, 1),
        target_buildings=10,
        target_users=5,
    )
    db_session.add(scorecard)
    await db_session.flush()
    assert scorecard.pilot_code == "test-pilot-001"


@pytest.mark.asyncio
async def test_create_pilot_metric(db_session):
    scorecard = PilotScorecard(
        id=uuid.uuid4(),
        pilot_name="Metric Test Pilot",
        pilot_code="metric-test-pilot",
        status="active",
        start_date=date(2026, 4, 1),
    )
    db_session.add(scorecard)
    await db_session.flush()

    metric = PilotMetric(
        id=uuid.uuid4(),
        scorecard_id=scorecard.id,
        dimension="recurring_usage",
        target_value=80.0,
        current_value=45.0,
        evidence_source="login_events",
        measured_at=datetime.now(UTC),
    )
    db_session.add(metric)
    await db_session.flush()
    assert metric.dimension == "recurring_usage"
    assert metric.current_value == 45.0


@pytest.mark.asyncio
async def test_create_case_study_template(db_session):
    template = CaseStudyTemplate(
        id=uuid.uuid4(),
        template_code="test-cs-001",
        title="Test Case Study",
        persona_target="property_manager",
        workflow_type="understand_building",
        narrative_structure={
            "before": "Before state",
            "trigger": "Trigger event",
            "after": "After state",
            "proof_points": ["Point 1", "Point 2"],
        },
        evidence_requirements=[
            {"type": "diagnostic_report", "source": "documents", "required": True},
        ],
        is_active=True,
    )
    db_session.add(template)
    await db_session.flush()
    assert template.workflow_type == "understand_building"


# ---- Schema Tests ----


def test_demo_scenario_read_schema():
    data = DemoScenarioRead(
        id=uuid.uuid4(),
        scenario_code="schema-test",
        title="Schema Test",
        persona_target="owner",
        starting_state_description="Test.",
        reveal_surfaces=["PassportCard"],
        proof_moment=None,
        action_moment=None,
        seed_key=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    assert data.scenario_code == "schema-test"


def test_pilot_scorecard_with_metrics_schema():
    scorecard_id = uuid.uuid4()
    data = PilotScorecardWithMetrics(
        id=scorecard_id,
        pilot_name="Schema Pilot",
        pilot_code="schema-pilot",
        status="active",
        start_date=date(2026, 4, 1),
        end_date=None,
        target_buildings=10,
        target_users=5,
        exit_state=None,
        exit_notes=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metrics=[
            PilotMetricRead(
                id=uuid.uuid4(),
                scorecard_id=scorecard_id,
                dimension="proof_reuse",
                target_value=50.0,
                current_value=25.0,
                evidence_source="proof_deliveries",
                notes=None,
                measured_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
        ],
    )
    assert len(data.metrics) == 1
    assert data.metrics[0].dimension == "proof_reuse"


def test_roi_report_schema():
    report = ROIReport(
        building_id=uuid.uuid4(),
        time_saved_hours=12.0,
        rework_avoided=3,
        blocker_days_saved=5.5,
        pack_reuse_count=3,
        breakdown=[
            ROIBreakdown(
                label="Obligations completed",
                value=8.0,
                unit="hours",
                evidence_count=4,
            ),
        ],
        evidence_sources=["obligations", "proof_deliveries"],
    )
    assert report.time_saved_hours == 12.0
    assert len(report.breakdown) == 1


def test_case_study_template_read_schema():
    data = CaseStudyTemplateRead(
        id=uuid.uuid4(),
        template_code="cs-schema-test",
        title="Schema Case Study",
        persona_target="owner",
        workflow_type="produce_dossier",
        narrative_structure={"before": "B", "trigger": "T", "after": "A", "proof_points": []},
        evidence_requirements=[],
        is_active=True,
        created_at=datetime.now(UTC),
    )
    assert data.workflow_type == "produce_dossier"


# ---- ROI Calculator Service Tests ----


@pytest.mark.asyncio
async def test_roi_calculator_empty_building(db_session, sample_building):
    """ROI for a building with no workflow events returns zeros."""
    report = await calculate_building_roi(db_session, sample_building.id)
    assert report.building_id == sample_building.id
    assert report.time_saved_hours == 0.0
    assert report.rework_avoided == 0
    assert report.blocker_days_saved == 0.0
    assert report.pack_reuse_count == 0
    assert report.breakdown == []
    assert report.evidence_sources == []


@pytest.mark.asyncio
async def test_roi_calculator_with_obligations(db_session, sample_building):
    """ROI counts completed obligations."""
    for i in range(3):
        ob = Obligation(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            title=f"Obligation {i}",
            obligation_type="regulatory_inspection",
            due_date=date(2026, 6, 1),
            status="completed",
            priority="medium",
        )
        db_session.add(ob)
    # Also add a non-completed one that should NOT count
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            title="Pending Ob",
            obligation_type="maintenance",
            due_date=date(2026, 7, 1),
            status="upcoming",
            priority="low",
        )
    )
    await db_session.flush()

    report = await calculate_building_roi(db_session, sample_building.id)
    assert report.time_saved_hours == 6.0  # 3 * 2.0
    assert "obligations" in report.evidence_sources


@pytest.mark.asyncio
async def test_roi_calculator_with_procedures(db_session, sample_building):
    """ROI counts approved permit procedures."""
    proc = PermitProcedure(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        procedure_type="suva_notification",
        title="SUVA Notification",
        status="approved",
    )
    db_session.add(proc)
    await db_session.flush()

    report = await calculate_building_roi(db_session, sample_building.id)
    assert report.time_saved_hours == 4.0  # 1 * 4.0
    assert "permit_procedures" in report.evidence_sources


# ---- API Route Tests ----


@pytest.mark.asyncio
async def test_list_demo_scenarios_api(client, auth_headers, db_session):
    scenario = DemoScenario(
        id=uuid.uuid4(),
        scenario_code="api-test-scenario",
        title="API Test Scenario",
        persona_target="contractor",
        starting_state_description="Test.",
        reveal_surfaces=["ControlTower"],
        is_active=True,
    )
    db_session.add(scenario)
    await db_session.flush()

    resp = await client.get("/api/v1/demo/scenarios", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(s["scenario_code"] == "api-test-scenario" for s in data)


@pytest.mark.asyncio
async def test_get_demo_scenario_runbook_api(client, auth_headers, db_session):
    scenario_id = uuid.uuid4()
    scenario = DemoScenario(
        id=scenario_id,
        scenario_code="runbook-api-test",
        title="Runbook API Test",
        persona_target="owner",
        starting_state_description="Test.",
        reveal_surfaces=["PassportCard"],
        is_active=True,
    )
    db_session.add(scenario)
    step = DemoRunbookStep(
        id=uuid.uuid4(),
        scenario_id=scenario_id,
        step_order=1,
        title="First Step",
        description="Do something.",
    )
    db_session.add(step)
    await db_session.flush()

    resp = await client.get("/api/v1/demo/scenarios/runbook-api-test/runbook", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_code"] == "runbook-api-test"
    assert len(data["runbook_steps"]) == 1


@pytest.mark.asyncio
async def test_get_demo_scenario_runbook_not_found(client, auth_headers):
    resp = await client.get("/api/v1/demo/scenarios/nonexistent/runbook", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_pilots_api(client, auth_headers, db_session):
    scorecard = PilotScorecard(
        id=uuid.uuid4(),
        pilot_name="API Pilot",
        pilot_code="api-pilot-001",
        status="active",
        start_date=date(2026, 5, 1),
    )
    db_session.add(scorecard)
    await db_session.flush()

    resp = await client.get("/api/v1/pilots", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(p["pilot_code"] == "api-pilot-001" for p in data)


@pytest.mark.asyncio
async def test_get_pilot_scorecard_api(client, auth_headers, db_session):
    sc_id = uuid.uuid4()
    scorecard = PilotScorecard(
        id=sc_id,
        pilot_name="Scorecard API Test",
        pilot_code="scorecard-api-test",
        status="active",
        start_date=date(2026, 5, 1),
    )
    db_session.add(scorecard)
    metric = PilotMetric(
        id=uuid.uuid4(),
        scorecard_id=sc_id,
        dimension="actor_spread",
        target_value=60.0,
        current_value=30.0,
        measured_at=datetime.now(UTC),
    )
    db_session.add(metric)
    await db_session.flush()

    resp = await client.get("/api/v1/pilots/scorecard-api-test/scorecard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pilot_code"] == "scorecard-api-test"
    assert len(data["metrics"]) == 1


@pytest.mark.asyncio
async def test_get_pilot_scorecard_not_found(client, auth_headers):
    resp = await client.get("/api/v1/pilots/nonexistent/scorecard", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_pilot_metric_api(client, auth_headers, db_session):
    scorecard = PilotScorecard(
        id=uuid.uuid4(),
        pilot_name="Metric Add Test",
        pilot_code="metric-add-test",
        status="active",
        start_date=date(2026, 5, 1),
    )
    db_session.add(scorecard)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/pilots/metric-add-test/metrics",
        headers=auth_headers,
        json={
            "dimension": "procedure_clarity",
            "target_value": 75.0,
            "current_value": 50.0,
            "evidence_source": "survey",
            "measured_at": datetime.now(UTC).isoformat(),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["dimension"] == "procedure_clarity"
    assert data["current_value"] == 50.0


@pytest.mark.asyncio
async def test_building_roi_api(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/roi", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["time_saved_hours"] == 0.0


@pytest.mark.asyncio
async def test_building_roi_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/roi", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_case_study_templates_api(client, auth_headers, db_session):
    template = CaseStudyTemplate(
        id=uuid.uuid4(),
        template_code="api-cs-test",
        title="API Case Study",
        persona_target="authority",
        workflow_type="know_blockers",
        narrative_structure={"before": "B", "trigger": "T", "after": "A", "proof_points": []},
        evidence_requirements=[],
        is_active=True,
    )
    db_session.add(template)
    await db_session.flush()

    resp = await client.get("/api/v1/case-study-templates", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(t["template_code"] == "api-cs-test" for t in data)


@pytest.mark.asyncio
async def test_get_case_study_template_api(client, auth_headers, db_session):
    template = CaseStudyTemplate(
        id=uuid.uuid4(),
        template_code="get-cs-test",
        title="Get Case Study",
        persona_target="fiduciary",
        workflow_type="reuse_proof",
        narrative_structure={"before": "B", "trigger": "T", "after": "A", "proof_points": ["P1"]},
        evidence_requirements=[{"type": "doc", "source": "vault", "required": True}],
        is_active=True,
    )
    db_session.add(template)
    await db_session.flush()

    resp = await client.get("/api/v1/case-study-templates/get-cs-test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_code"] == "get-cs-test"
    assert data["workflow_type"] == "reuse_proof"


@pytest.mark.asyncio
async def test_get_case_study_template_not_found(client, auth_headers):
    resp = await client.get("/api/v1/case-study-templates/nonexistent", headers=auth_headers)
    assert resp.status_code == 404
