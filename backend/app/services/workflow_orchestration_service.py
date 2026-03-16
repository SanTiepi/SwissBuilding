"""Workflow Orchestration Service — stateless state machine for multi-step processes.

This service manages workflow instances entirely in-memory (module-level dict).
No new SQLAlchemy models are created. Workflow state is stored in _WORKFLOWS.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

# ---------------------------------------------------------------------------
# Workflow type → ordered step names
# ---------------------------------------------------------------------------
WORKFLOW_STEPS: dict[str, list[str]] = {
    "diagnostic_process": [
        "planning",
        "field_inspection",
        "sampling",
        "lab_analysis",
        "report",
        "validation",
    ],
    "remediation_process": [
        "assessment",
        "work_plan",
        "authorization",
        "execution",
        "verification",
        "clearance",
    ],
    "clearance_process": [
        "inspection",
        "sampling",
        "analysis",
        "report",
        "authority_submission",
        "approval",
    ],
    "renovation_readiness": [
        "diagnostic_review",
        "risk_assessment",
        "cost_estimation",
        "planning",
        "contractor_selection",
        "ready",
    ],
}

VALID_ACTIONS = {"complete_step", "skip_step", "reject_step", "request_review"}

# ---------------------------------------------------------------------------
# In-memory store  (keyed by workflow UUID)
# ---------------------------------------------------------------------------
_WORKFLOWS: dict[uuid.UUID, dict] = {}
_TRANSITIONS: dict[uuid.UUID, list[dict]] = {}


def _reset_store() -> None:
    """Clear in-memory store — used by tests."""
    _WORKFLOWS.clear()
    _TRANSITIONS.clear()


def _make_steps(workflow_type: str) -> list[dict]:
    step_names = WORKFLOW_STEPS[workflow_type]
    now = datetime.now(UTC)
    steps = []
    for i, name in enumerate(step_names):
        steps.append(
            {
                "index": i,
                "name": name,
                "status": "in_progress" if i == 0 else "pending",
                "started_at": now if i == 0 else None,
                "completed_at": None,
                "actor_id": None,
                "notes": None,
            }
        )
    return steps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_workflow(
    db: AsyncSession,
    building_id: uuid.UUID,
    workflow_type: str,
    created_by: uuid.UUID,
) -> dict:
    """Create a new workflow instance for a building.

    Validates building exists and workflow_type is known.
    Returns the full workflow instance dict.
    """
    # Validate workflow type
    if workflow_type not in WORKFLOW_STEPS:
        raise ValueError(f"Unknown workflow_type '{workflow_type}'. Valid types: {', '.join(sorted(WORKFLOW_STEPS))}")

    # Validate building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Building {building_id} not found")

    now = datetime.now(UTC)
    wf_id = uuid.uuid4()
    workflow = {
        "id": wf_id,
        "building_id": building_id,
        "workflow_type": workflow_type,
        "status": "active",
        "current_step_index": 0,
        "steps": _make_steps(workflow_type),
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    _WORKFLOWS[wf_id] = workflow
    _TRANSITIONS[wf_id] = []
    return workflow


async def advance_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID,
    notes: str | None = None,
) -> dict:
    """Advance or modify workflow at its current step.

    Actions:
      - complete_step: mark current step done, move to next (or finish).
      - skip_step: skip current step, move to next.
      - reject_step: mark current step rejected, block the workflow.
      - request_review: keep current step but record review request.

    Returns the updated workflow instance dict.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"Invalid action '{action}'. Valid: {', '.join(sorted(VALID_ACTIONS))}")

    workflow = _WORKFLOWS.get(workflow_id)
    if workflow is None:
        raise ValueError(f"Workflow {workflow_id} not found")

    if workflow["status"] != "active":
        raise ValueError(f"Workflow is '{workflow['status']}', cannot advance")

    now = datetime.now(UTC)
    idx = workflow["current_step_index"]
    current_step = workflow["steps"][idx]
    from_step_name = current_step["name"]
    to_step_name: str | None = None

    if action == "complete_step":
        current_step["status"] = "completed"
        current_step["completed_at"] = now
        current_step["actor_id"] = actor_id
        if notes:
            current_step["notes"] = notes
        # Move to next step or finish
        next_idx = idx + 1
        if next_idx < len(workflow["steps"]):
            workflow["current_step_index"] = next_idx
            workflow["steps"][next_idx]["status"] = "in_progress"
            workflow["steps"][next_idx]["started_at"] = now
            to_step_name = workflow["steps"][next_idx]["name"]
        else:
            workflow["status"] = "completed"

    elif action == "skip_step":
        current_step["status"] = "skipped"
        current_step["completed_at"] = now
        current_step["actor_id"] = actor_id
        if notes:
            current_step["notes"] = notes
        next_idx = idx + 1
        if next_idx < len(workflow["steps"]):
            workflow["current_step_index"] = next_idx
            workflow["steps"][next_idx]["status"] = "in_progress"
            workflow["steps"][next_idx]["started_at"] = now
            to_step_name = workflow["steps"][next_idx]["name"]
        else:
            workflow["status"] = "completed"

    elif action == "reject_step":
        current_step["status"] = "rejected"
        current_step["completed_at"] = now
        current_step["actor_id"] = actor_id
        if notes:
            current_step["notes"] = notes
        workflow["status"] = "blocked"

    elif action == "request_review":
        # Step stays in_progress, just record the transition
        if notes:
            current_step["notes"] = notes
        current_step["actor_id"] = actor_id
        to_step_name = from_step_name  # stays on same step

    workflow["updated_at"] = now

    _TRANSITIONS[workflow_id].append(
        {
            "from_step": from_step_name,
            "to_step": to_step_name,
            "action": action,
            "actor_id": actor_id,
            "notes": notes,
            "timestamp": now,
        }
    )

    return workflow


async def get_workflow_status(
    db: AsyncSession,
    workflow_id: uuid.UUID,
) -> dict:
    """Full workflow status: steps, progression, blockers, transition history."""
    workflow = _WORKFLOWS.get(workflow_id)
    if workflow is None:
        raise ValueError(f"Workflow {workflow_id} not found")

    steps = workflow["steps"]
    total = len(steps)
    completed = sum(1 for s in steps if s["status"] in ("completed", "skipped"))
    progress = (completed / total * 100) if total > 0 else 0.0

    current_step = None
    if workflow["status"] == "active" and workflow["current_step_index"] < total:
        current_step = steps[workflow["current_step_index"]]

    blockers: list[str] = []
    if workflow["status"] == "blocked":
        rejected = [s for s in steps if s["status"] == "rejected"]
        for s in rejected:
            blockers.append(f"Step '{s['name']}' was rejected")

    return {
        "workflow": workflow,
        "progress_percent": round(progress, 1),
        "completed_steps": completed,
        "total_steps": total,
        "current_step": current_step,
        "blockers": blockers,
        "transitions": _TRANSITIONS.get(workflow_id, []),
    }


async def get_building_workflows(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> dict:
    """List all workflows for a building with summary of progression."""
    # Validate building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Building {building_id} not found")

    summaries = []
    for wf in _WORKFLOWS.values():
        if wf["building_id"] != building_id:
            continue
        steps = wf["steps"]
        total = len(steps)
        completed = sum(1 for s in steps if s["status"] in ("completed", "skipped"))
        progress = (completed / total * 100) if total > 0 else 0.0
        current_name = None
        if wf["status"] == "active" and wf["current_step_index"] < total:
            current_name = steps[wf["current_step_index"]]["name"]
        summaries.append(
            {
                "id": wf["id"],
                "workflow_type": wf["workflow_type"],
                "status": wf["status"],
                "progress_percent": round(progress, 1),
                "current_step_name": current_name,
                "created_at": wf["created_at"],
            }
        )

    return {
        "building_id": building_id,
        "workflows": summaries,
        "total": len(summaries),
    }
