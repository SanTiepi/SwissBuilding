"""BatiConnect — Growth Stack schemas (Subscription lifecycle, AI extraction, workspaces, flywheel)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Subscription lifecycle
# ---------------------------------------------------------------------------


class SubscriptionChangeRead(BaseModel):
    id: UUID
    subscription_id: UUID
    change_type: str
    old_plan: str | None = None
    new_plan: str | None = None
    changed_by_user_id: UUID | None = None
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyEligibilitySummary(BaseModel):
    company_profile_id: UUID
    verified: bool
    subscription_active: bool
    eligible: bool
    blockers: list[str]


class SubscriptionLifecycleView(BaseModel):
    subscription_id: UUID
    company_profile_id: UUID
    current_plan: str
    current_status: str
    changes: list[SubscriptionChangeRead]


# ---------------------------------------------------------------------------
# AI Extraction
# ---------------------------------------------------------------------------


class QuoteExtractionDraft(BaseModel):
    scope_items: list[str]
    exclusions: list[str]
    timeline_weeks: int | None = None
    amount_chf: float | None = None
    confidence_per_field: dict[str, float]
    ambiguous_fields: list[dict]
    unknown_fields: list[dict]


class CompletionExtractionDraft(BaseModel):
    completed_items: list[str]
    residual_items: list[str]
    final_amount_chf: float | None = None
    confidence_per_field: dict[str, float]
    ambiguous_fields: list[dict]
    unknown_fields: list[dict]


class AIExtractionRead(BaseModel):
    id: UUID
    extraction_type: str
    source_document_id: UUID | None = None
    source_filename: str | None = None
    input_hash: str
    output_data: dict | None = None
    confidence_score: float | None = None
    ai_model: str | None = None
    ambiguous_fields: list[dict] | None = None
    unknown_fields: list[dict] | None = None
    status: str
    confirmed_by_user_id: UUID | None = None
    confirmed_at: datetime | None = None
    created_at: datetime
    provider_name: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ExtractionInput(BaseModel):
    text: str | None = None
    source_filename: str | None = None
    source_document_id: UUID | None = None


class ExtractionCorrection(BaseModel):
    corrected_data: dict
    notes: str | None = None


class ExtractionRejection(BaseModel):
    reason: str


# ---------------------------------------------------------------------------
# Workspace read models
# ---------------------------------------------------------------------------


class CompanyWorkspaceSummary(BaseModel):
    company_profile_id: UUID
    company_name: str
    is_verified: bool
    subscription_status: str | None = None
    subscription_plan: str | None = None
    pending_invitations: int
    active_rfqs: int
    draft_quotes: int
    awards_won: int
    completions_pending: int
    reviews_published: int


class OperatorRemediationQueue(BaseModel):
    active_rfqs: int
    quotes_received: int
    awards_pending: int
    completions_awaiting: int
    post_works_open: int


class QuoteComparisonRow(BaseModel):
    company_name: str
    amount_chf: float | None = None
    timeline_weeks: int | None = None
    scope_items: list[str]
    exclusions: list[str]
    confidence: float | None = None
    ambiguous_fields: list[dict]
    submitted_at: datetime | None = None


class QuoteComparisonMatrix(BaseModel):
    request_id: UUID
    rows: list[QuoteComparisonRow]


class CompletionClosureSummary(BaseModel):
    completion_id: UUID
    completion_status: str
    intervention_id: UUID | None = None
    post_works_link_status: str | None = None
    review_status: str | None = None


# ---------------------------------------------------------------------------
# Flywheel metrics
# ---------------------------------------------------------------------------


class FlywheelMetrics(BaseModel):
    total_extractions: int
    confirmation_rate: float
    correction_rate: float
    rejection_rate: float
    avg_cycle_time_days: float | None = None
    total_completed_cycles: int
    total_reviews_published: int
    knowledge_density: float
