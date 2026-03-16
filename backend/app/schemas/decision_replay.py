"""Pydantic v2 schemas for the Decision Replay service."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DecisionRecordCreate(BaseModel):
    building_id: UUID
    decision_type: str
    title: str
    rationale: str
    alternatives_considered: str | None = None
    context_snapshot: dict | None = None
    entity_type: str
    entity_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class DecisionRecordRead(BaseModel):
    id: UUID
    building_id: UUID
    decision_type: str
    title: str
    rationale: str
    alternatives_considered: str | None = None
    decided_by: UUID
    decided_at: datetime
    context_snapshot: dict | None = None
    outcome: str | None = None
    outcome_notes: str | None = None
    entity_type: str
    entity_id: UUID | None = None
    decided_by_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DecisionRecordUpdate(BaseModel):
    outcome: str | None = None
    outcome_notes: str | None = None
    rationale: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DecisionTimeline(BaseModel):
    building_id: UUID
    decisions: list[DecisionRecordRead]
    total_decisions: int

    model_config = ConfigDict(from_attributes=True)


class DecisionPattern(BaseModel):
    decision_type: str
    count: int
    avg_days_between: float | None = None
    most_common_outcome: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DecisionContext(BaseModel):
    building_id: UUID
    at_decision_time: dict
    current_state: dict
    state_changed: bool

    model_config = ConfigDict(from_attributes=True)


class DecisionImpactAnalysis(BaseModel):
    decision_id: UUID
    decision_type: str
    title: str
    before_state: dict
    after_state: dict | None = None
    impact_summary: str | None = None
    days_since_decision: int

    model_config = ConfigDict(from_attributes=True)
