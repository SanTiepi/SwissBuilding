"""Pydantic v2 schemas for Workflow Orchestration."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    index: int
    name: str
    status: str  # pending, in_progress, completed, skipped, rejected
    started_at: datetime | None = None
    completed_at: datetime | None = None
    actor_id: UUID | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowTransition(BaseModel):
    """A recorded transition between workflow steps."""

    from_step: str
    to_step: str | None
    action: str  # complete_step, skip_step, reject_step, request_review
    actor_id: UUID
    notes: str | None = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowCreate(BaseModel):
    """Request body for creating a workflow."""

    building_id: UUID
    workflow_type: str  # diagnostic_process, remediation_process, clearance_process, renovation_readiness

    model_config = ConfigDict(from_attributes=True)


class WorkflowAdvance(BaseModel):
    """Request body for advancing a workflow."""

    action: str  # complete_step, skip_step, reject_step, request_review
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowInstance(BaseModel):
    """A workflow instance."""

    id: UUID
    building_id: UUID
    workflow_type: str
    status: str  # active, completed, cancelled, blocked
    current_step_index: int
    steps: list[WorkflowStep]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowStatus(BaseModel):
    """Full workflow status with progression and history."""

    workflow: WorkflowInstance
    progress_percent: float
    completed_steps: int
    total_steps: int
    current_step: WorkflowStep | None
    blockers: list[str]
    transitions: list[WorkflowTransition]

    model_config = ConfigDict(from_attributes=True)


class WorkflowSummary(BaseModel):
    """Summary of a workflow for listing."""

    id: UUID
    workflow_type: str
    status: str
    progress_percent: float
    current_step_name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingWorkflows(BaseModel):
    """All workflows for a building."""

    building_id: UUID
    workflows: list[WorkflowSummary]
    total: int

    model_config = ConfigDict(from_attributes=True)
