"""Pydantic v2 schemas for Building Intent, Question, DecisionContext, SafeToXState."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# BuildingIntent
# ---------------------------------------------------------------------------


class BuildingIntentCreate(BaseModel):
    intent_type: str = Field(
        ...,
        description="One of: sell, buy, renovate, insure, finance, lease, transfer, demolish, assess, comply, maintain, remediate, other",
    )
    title: str = Field(..., max_length=255)
    description: str | None = None
    target_date: datetime | None = None
    organization_id: UUID | None = None


class BuildingIntentRead(BaseModel):
    id: UUID
    building_id: UUID
    organization_id: UUID | None = None
    created_by_id: UUID
    intent_type: str
    title: str
    description: str | None = None
    target_date: datetime | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# BuildingQuestion
# ---------------------------------------------------------------------------


class BuildingQuestionCreate(BaseModel):
    question_type: str = Field(
        ...,
        description="One of: safe_to_start, safe_to_sell, safe_to_insure, safe_to_finance, safe_to_lease, safe_to_transfer, safe_to_demolish, safe_to_tender, what_blocks, what_missing, what_contradicts, what_changed, what_expires, what_costs, what_next, custom",
    )
    question_text: str = Field(..., max_length=500)
    intent_id: UUID | None = None


class BuildingQuestionRead(BaseModel):
    id: UUID
    intent_id: UUID | None = None
    building_id: UUID
    asked_by_id: UUID
    question_type: str
    question_text: str
    status: str
    answered_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# DecisionContext
# ---------------------------------------------------------------------------


class DecisionContextRead(BaseModel):
    id: UUID
    question_id: UUID
    building_id: UUID
    relevant_evidence_ids: list | None = None
    relevant_claims_ids: list | None = None
    applicable_rules: list | None = None
    blockers: list | None = None
    conditions: list | None = None
    overall_confidence: float | None = None
    data_freshness: str | None = None
    contradiction_count: int = 0
    coverage_assessment: str | None = None
    computed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# SafeToXState
# ---------------------------------------------------------------------------


class SafeToXStateRead(BaseModel):
    id: UUID
    question_id: UUID
    building_id: UUID
    intent_id: UUID | None = None
    safe_to_type: str
    verdict: str
    verdict_summary: str
    decision_context_id: UUID | None = None
    blockers: list | None = None
    conditions: list | None = None
    evaluated_at: datetime | None = None
    evaluated_by: str | None = None
    rule_basis: list | None = None
    confidence: float | None = None
    valid_until: datetime | None = None
    superseded_by_id: UUID | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Composite responses
# ---------------------------------------------------------------------------


class QuestionWithAnswer(BaseModel):
    """A question with its decision context and safe-to-x verdict."""

    question: BuildingQuestionRead
    decision_context: DecisionContextRead | None = None
    safe_to_x_state: SafeToXStateRead | None = None


class SafeToXSummary(BaseModel):
    """All current SafeToX verdicts for a building."""

    building_id: UUID
    verdicts: list[SafeToXStateRead]
    evaluated_at: datetime
