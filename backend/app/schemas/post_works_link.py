"""BatiConnect — Lot 4: PostWorksLink + DomainEvent + AIFeedback schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# PostWorksLink
# ---------------------------------------------------------------------------


class PostWorksLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    completion_confirmation_id: UUID
    intervention_id: UUID
    before_snapshot_id: UUID | None = None
    after_snapshot_id: UUID | None = None
    status: str
    grade_delta: dict[str, Any] | None = None
    trust_delta: dict[str, Any] | None = None
    completeness_delta: dict[str, Any] | None = None
    residual_risks: list[dict[str, Any]] | None = None
    drafted_at: datetime | None = None
    finalized_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PostWorksDraftRequest(BaseModel):
    """Body is intentionally empty — completion_confirmation_id comes from path."""

    pass


class PostWorksFinalizeRequest(BaseModel):
    """Body is intentionally empty — post_works_link_id resolved from path."""

    pass


# ---------------------------------------------------------------------------
# DomainEvent
# ---------------------------------------------------------------------------


class DomainEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any] | None = None
    actor_user_id: UUID | None = None
    occurred_at: datetime
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# AIFeedback
# ---------------------------------------------------------------------------


class AIFeedbackCreate(BaseModel):
    feedback_type: str  # confirm | correct | reject
    entity_type: str  # post_works_state | extraction | classification | comparison
    entity_id: UUID
    original_output: dict[str, Any] | None = None
    corrected_output: dict[str, Any] | None = None
    ai_model: str | None = None
    confidence: float | None = None
    notes: str | None = None


class AIFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feedback_type: str
    entity_type: str
    entity_id: UUID
    original_output: dict[str, Any] | None = None
    corrected_output: dict[str, Any] | None = None
    ai_model: str | None = None
    confidence: float | None = None
    user_id: UUID
    notes: str | None = None
    created_at: datetime | None = None
