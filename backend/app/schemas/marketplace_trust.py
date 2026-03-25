"""BatiConnect — Marketplace Trust schemas (Award, Completion, Review)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# AwardConfirmation
# ---------------------------------------------------------------------------


class AwardConfirmationCreate(BaseModel):
    quote_id: UUID
    conditions: str | None = None


class AwardConfirmationRead(BaseModel):
    id: UUID
    client_request_id: UUID
    quote_id: UUID
    company_profile_id: UUID
    awarded_by_user_id: UUID
    award_amount_chf: Decimal | None
    conditions: str | None
    content_hash: str | None
    awarded_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# CompletionConfirmation
# ---------------------------------------------------------------------------


class CompletionConfirmationRead(BaseModel):
    id: UUID
    award_confirmation_id: UUID
    client_confirmed: bool
    client_confirmed_at: datetime | None
    client_confirmed_by_user_id: UUID | None
    company_confirmed: bool
    company_confirmed_at: datetime | None
    company_confirmed_by_user_id: UUID | None
    status: str
    completion_notes: str | None
    final_amount_chf: Decimal | None
    content_hash: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CompletionConfirmAction(BaseModel):
    notes: str | None = None
    final_amount_chf: Decimal | None = None


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewCreate(BaseModel):
    completion_confirmation_id: UUID
    client_request_id: UUID
    company_profile_id: UUID
    reviewer_type: str = Field(..., pattern=r"^(client|company)$")
    rating: int = Field(..., ge=1, le=5)
    quality_score: int | None = Field(None, ge=1, le=5)
    timeliness_score: int | None = Field(None, ge=1, le=5)
    communication_score: int | None = Field(None, ge=1, le=5)
    comment: str | None = None


class ReviewRead(BaseModel):
    id: UUID
    completion_confirmation_id: UUID
    client_request_id: UUID
    company_profile_id: UUID
    reviewer_user_id: UUID
    reviewer_type: str
    rating: int
    quality_score: int | None
    timeliness_score: int | None
    communication_score: int | None
    comment: str | None
    status: str
    moderated_by_user_id: UUID | None
    moderated_at: datetime | None
    moderation_notes: str | None
    rejection_reason: str | None
    submitted_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ReviewModerateAction(BaseModel):
    decision: str = Field(..., pattern=r"^(approve|reject)$")
    notes: str | None = None
    rejection_reason: str | None = None


# ---------------------------------------------------------------------------
# Rating Summary
# ---------------------------------------------------------------------------


class RatingSummary(BaseModel):
    company_profile_id: UUID
    average_rating: float | None
    total_reviews: int
    rating_breakdown: dict[str, int]  # {"1": 0, "2": 0, "3": 1, "4": 2, "5": 0}
    average_quality: float | None
    average_timeliness: float | None
    average_communication: float | None
