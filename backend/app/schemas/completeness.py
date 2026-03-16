"""Pydantic v2 schemas for the Completeness Engine."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompletenessCheck(BaseModel):
    """A single check in the completeness evaluation."""

    id: str
    category: str
    label_key: str
    status: str  # complete, missing, partial, not_applicable
    weight: float
    details: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CompletenessResult(BaseModel):
    """Overall completeness evaluation for a building dossier."""

    building_id: UUID
    workflow_stage: str  # avt or apt
    overall_score: float
    checks: list[CompletenessCheck]
    missing_items: list[str]
    ready_to_proceed: bool
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
