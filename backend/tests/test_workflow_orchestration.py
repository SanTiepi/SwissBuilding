"""Tests for Workflow Orchestration service and API."""

import uuid

import pytest

from app.services.workflow_orchestration_service import (
    WORKFLOW_STEPS,
    _reset_store,
    advance_workflow,
    create_workflow,
    get_building_workflows,
    get_workflow_status,
)


@pytest.fixture(autouse=True)
def clean_workflow_store():
    """Clear in-memory workflow store before each test."""
    _reset_store()
    yield
    _reset_store()


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestCreateWorkflow:
    async def test_create_diagnostic_process(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        assert wf["workflow_type"] == "diagnostic_process"
        assert wf["status"] == "active"
        assert wf["current_step_index"] == 0
        assert len(wf["steps"]) == 6
        assert wf["steps"][0]["name"] == "planning"
        assert wf["steps"][0]["status"] == "in_progress"
        assert wf["steps"][1]["status"] == "pending"

    async def test_create_remediation_process(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "remediation_process", admin_user.id)
        assert wf["workflow_type"] == "remediation_process"
        assert len(wf["steps"]) == 6
        assert wf["steps"][0]["name"] == "assessment"

    async def test_create_clearance_process(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "clearance_process", admin_user.id)
        assert wf["workflow_type"] == "clearance_process"
        assert wf["steps"][0]["name"] == "inspection"

    async def test_create_renovation_readiness(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "renovation_readiness", admin_user.id)
        assert wf["workflow_type"] == "renovation_readiness"
        assert wf["steps"][-1]["name"] == "ready"

    async def test_create_unknown_type_raises(self, db_session, sample_building, admin_user):
        with pytest.raises(ValueError, match="Unknown workflow_type"):
            await create_workflow(db_session, sample_building.id, "invalid_type", admin_user.id)

    async def test_create_nonexistent_building_raises(self, db_session, admin_user):
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await create_workflow(db_session, fake_id, "diagnostic_process", admin_user.id)

    async def test_create_assigns_uuid(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        assert isinstance(wf["id"], uuid.UUID)

    async def test_first_step_has_started_at(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        assert wf["steps"][0]["started_at"] is not None
        assert wf["steps"][1]["started_at"] is None


class TestAdvanceWorkflow:
    async def test_complete_step_advances(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        wf = await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)
        assert wf["current_step_index"] == 1
        assert wf["steps"][0]["status"] == "completed"
        assert wf["steps"][1]["status"] == "in_progress"

    async def test_complete_all_steps_finishes(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        for _ in range(6):
            wf = await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)
        assert wf["status"] == "completed"

    async def test_skip_step(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        wf = await advance_workflow(db_session, wf["id"], "skip_step", admin_user.id, "Not needed")
        assert wf["steps"][0]["status"] == "skipped"
        assert wf["steps"][0]["notes"] == "Not needed"
        assert wf["current_step_index"] == 1

    async def test_reject_step_blocks(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        wf = await advance_workflow(db_session, wf["id"], "reject_step", admin_user.id, "Bad data")
        assert wf["status"] == "blocked"
        assert wf["steps"][0]["status"] == "rejected"

    async def test_cannot_advance_blocked(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        await advance_workflow(db_session, wf["id"], "reject_step", admin_user.id)
        with pytest.raises(ValueError, match="blocked"):
            await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)

    async def test_cannot_advance_completed(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "clearance_process", admin_user.id)
        for _ in range(6):
            wf = await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)
        with pytest.raises(ValueError, match="completed"):
            await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)

    async def test_request_review_stays(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        wf = await advance_workflow(db_session, wf["id"], "request_review", admin_user.id, "Please check")
        assert wf["current_step_index"] == 0
        assert wf["steps"][0]["status"] == "in_progress"
        assert wf["steps"][0]["notes"] == "Please check"

    async def test_invalid_action_raises(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        with pytest.raises(ValueError, match="Invalid action"):
            await advance_workflow(db_session, wf["id"], "destroy", admin_user.id)

    async def test_nonexistent_workflow_raises(self, db_session, admin_user):
        with pytest.raises(ValueError, match="not found"):
            await advance_workflow(db_session, uuid.uuid4(), "complete_step", admin_user.id)

    async def test_skip_all_steps_completes(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "remediation_process", admin_user.id)
        for _ in range(6):
            wf = await advance_workflow(db_session, wf["id"], "skip_step", admin_user.id)
        assert wf["status"] == "completed"


class TestGetWorkflowStatus:
    async def test_status_initial(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        status = await get_workflow_status(db_session, wf["id"])
        assert status["progress_percent"] == 0.0
        assert status["completed_steps"] == 0
        assert status["total_steps"] == 6
        assert status["current_step"]["name"] == "planning"
        assert status["blockers"] == []

    async def test_status_after_advance(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)
        status = await get_workflow_status(db_session, wf["id"])
        assert status["progress_percent"] == pytest.approx(16.7, abs=0.1)
        assert status["completed_steps"] == 1
        assert status["current_step"]["name"] == "field_inspection"

    async def test_status_blocked_has_blockers(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        await advance_workflow(db_session, wf["id"], "reject_step", admin_user.id, "Bad")
        status = await get_workflow_status(db_session, wf["id"])
        assert len(status["blockers"]) == 1
        assert "rejected" in status["blockers"][0]

    async def test_status_transitions_recorded(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)
        await advance_workflow(db_session, wf["id"], "skip_step", admin_user.id)
        status = await get_workflow_status(db_session, wf["id"])
        assert len(status["transitions"]) == 2
        assert status["transitions"][0]["action"] == "complete_step"
        assert status["transitions"][1]["action"] == "skip_step"

    async def test_status_nonexistent_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_workflow_status(db_session, uuid.uuid4())


class TestGetBuildingWorkflows:
    async def test_empty_building(self, db_session, sample_building, admin_user):
        result = await get_building_workflows(db_session, sample_building.id)
        assert result["total"] == 0
        assert result["workflows"] == []

    async def test_multiple_workflows(self, db_session, sample_building, admin_user):
        await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        await create_workflow(db_session, sample_building.id, "remediation_process", admin_user.id)
        result = await get_building_workflows(db_session, sample_building.id)
        assert result["total"] == 2
        types = {w["workflow_type"] for w in result["workflows"]}
        assert types == {"diagnostic_process", "remediation_process"}

    async def test_nonexistent_building_raises(self, db_session, admin_user):
        with pytest.raises(ValueError, match="not found"):
            await get_building_workflows(db_session, uuid.uuid4())

    async def test_summary_has_progress(self, db_session, sample_building, admin_user):
        wf = await create_workflow(db_session, sample_building.id, "diagnostic_process", admin_user.id)
        await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)
        result = await get_building_workflows(db_session, sample_building.id)
        summary = result["workflows"][0]
        assert summary["progress_percent"] == pytest.approx(16.7, abs=0.1)
        assert summary["current_step_name"] == "field_inspection"


class TestAllWorkflowTypes:
    @pytest.mark.parametrize("wf_type", list(WORKFLOW_STEPS.keys()))
    async def test_all_types_have_six_steps(self, db_session, sample_building, admin_user, wf_type):
        wf = await create_workflow(db_session, sample_building.id, wf_type, admin_user.id)
        assert len(wf["steps"]) == 6

    @pytest.mark.parametrize("wf_type", list(WORKFLOW_STEPS.keys()))
    async def test_all_types_completable(self, db_session, sample_building, admin_user, wf_type):
        wf = await create_workflow(db_session, sample_building.id, wf_type, admin_user.id)
        for _ in range(6):
            wf = await advance_workflow(db_session, wf["id"], "complete_step", admin_user.id)
        assert wf["status"] == "completed"
