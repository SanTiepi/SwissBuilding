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


# ── Decision Replay Layer (basis snapshot & staleness) ──


class DecisionReplayRead(BaseModel):
    """Lecture d'un replay de decision avec son instantane de base."""

    id: UUID
    building_id: UUID
    decision_id: UUID
    basis_snapshot: dict | None = None
    trust_state_at_decision: dict | None = None
    completeness_at_decision: float | None = None
    readiness_at_decision: dict | None = None
    changes_since: list[dict] | None = None
    basis_still_valid: bool | None = None
    invalidated_by: list[dict] | None = None
    replay_status: str
    replay_summary: str | None = None
    replayed_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DecisionReplayListResponse(BaseModel):
    """Liste des replays pour un batiment."""

    building_id: UUID
    replays: list[DecisionReplayRead]
    total: int

    model_config = ConfigDict(from_attributes=True)


class StaleDecisionRead(BaseModel):
    """Resume d'une decision dont la base a change."""

    decision_id: UUID
    decision_type: str
    title: str
    outcome: str
    decided_at: datetime | None = None
    replay_status: str
    replay_summary: str | None = None
    changes_count: int = 0
    invalidation_reasons: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class BasisValidityCheck(BaseModel):
    """Resultat de la verification de validite de la base."""

    replay_id: UUID
    decision_id: UUID
    basis_still_valid: bool
    replay_status: str
    changes_detected: list[dict]
    invalidation_reasons: list[str]
    replay_summary: str

    model_config = ConfigDict(from_attributes=True)
