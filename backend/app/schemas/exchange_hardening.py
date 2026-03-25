"""BatiConnect — Exchange Hardening + Contributor Gateway schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- PassportStateDiff ---


class DiffSectionChange(BaseModel):
    section: str
    field: str
    old: str | None = None
    new: str | None = None


class DiffSummary(BaseModel):
    added_sections: list[str] = []
    removed_sections: list[str] = []
    changed_sections: list[DiffSectionChange] = []


class PassportStateDiffRead(BaseModel):
    id: UUID
    publication_id: UUID
    prior_publication_id: UUID | None
    diff_summary: dict | None
    sections_changed_count: int
    computed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- ExchangeValidationReport ---


class ValidationError(BaseModel):
    check: str
    message: str
    severity: str = "error"


class ExchangeValidationReportRead(BaseModel):
    id: UUID
    import_receipt_id: UUID
    schema_valid: bool | None
    contract_valid: bool | None
    version_valid: bool | None
    hash_valid: bool | None
    identity_safe: bool | None
    validation_errors: list[dict] | None
    overall_status: str
    validated_at: datetime | None
    validated_by_user_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportReviewRequest(BaseModel):
    decision: str  # passed|failed|review_required


# --- ExternalRelianceSignal ---


class RelianceSignalCreate(BaseModel):
    publication_id: UUID | None = None
    import_receipt_id: UUID | None = None
    signal_type: str  # consumed|acknowledged|superseded|disputed
    partner_org_id: UUID | None = None
    notes: str | None = None


class RelianceSignalRead(BaseModel):
    id: UUID
    publication_id: UUID | None
    import_receipt_id: UUID | None
    signal_type: str
    partner_org_id: UUID | None
    notes: str | None
    recorded_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PartnerWebhookSubscription ---


class WebhookSubscriptionCreate(BaseModel):
    partner_org_id: UUID
    endpoint_url: str
    hmac_secret: str
    subscribed_events: list[str] = []
    is_active: bool = True


class WebhookSubscriptionRead(BaseModel):
    id: UUID
    partner_org_id: UUID
    endpoint_url: str
    subscribed_events: list[str] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryAttemptRead(BaseModel):
    id: UUID
    subscription_id: UUID
    event_type: str
    idempotency_key: str
    payload: dict | None
    status: str
    http_status: int | None
    error_message: str | None
    attempt_count: int
    last_attempt_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- ContributorGatewayRequest ---


class ContributorRequestCreate(BaseModel):
    building_id: UUID
    contributor_type: str  # contractor|lab
    scope_description: str | None = None
    expires_in_hours: int = 72
    linked_procedure_id: UUID | None = None
    linked_remediation_id: UUID | None = None


class ContributorRequestRead(BaseModel):
    id: UUID
    building_id: UUID
    contributor_type: str
    scope_description: str | None
    access_token: str
    expires_at: datetime
    status: str
    created_by_user_id: UUID
    linked_procedure_id: UUID | None
    linked_remediation_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- ContributorSubmission ---


class ContributorSubmissionCreate(BaseModel):
    contributor_org_id: UUID | None = None
    contributor_name: str | None = None
    submission_type: str  # completion_report|lab_results|certificate|attestation|photo_evidence|other
    file_url: str | None = None
    structured_data: dict | None = None
    notes: str | None = None


class ContributorSubmissionRead(BaseModel):
    id: UUID
    request_id: UUID
    contributor_org_id: UUID | None
    contributor_name: str | None
    submission_type: str
    file_url: str | None
    structured_data: dict | None
    notes: str | None
    status: str
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionRejectRequest(BaseModel):
    notes: str | None = None


# --- ContributorReceipt ---


class ContributorReceiptRead(BaseModel):
    id: UUID
    submission_id: UUID
    document_id: UUID | None
    evidence_link_id: UUID | None
    proof_delivery_id: UUID | None
    receipt_hash: str
    accepted_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
