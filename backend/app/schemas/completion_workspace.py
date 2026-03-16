"""Pydantic v2 schemas for the Completion Workspace."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompletionStep(BaseModel):
    """A single actionable step toward dossier completion."""

    id: UUID
    step_number: int
    category: str  # evidence, diagnostic, documentation, verification, administrative
    title: str
    description: str
    priority: str  # critical, high, medium, low
    status: str  # pending, in_progress, completed, skipped, blocked
    blocker_reason: str | None = None
    estimated_effort_minutes: int | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    depends_on: list[UUID] = []

    model_config = ConfigDict(from_attributes=True)


class CompletionWorkspace(BaseModel):
    """Guided completion workspace for a building dossier."""

    building_id: UUID
    total_steps: int
    completed_steps: int
    progress_percent: float
    steps: list[CompletionStep]
    overall_priority: str  # critical, high, medium, low
    estimated_total_effort_minutes: int | None = None
    next_recommended_step: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class StepStatusUpdate(BaseModel):
    """Payload for updating a step's status."""

    status: str  # pending, in_progress, completed, skipped, blocked
    blocker_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)
