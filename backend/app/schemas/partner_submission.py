"""BatiConnect -- Partner Submission schemas.

Input/output types for the governed partner submission flow.
Every submission goes through contract validation + audit trail.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PartnerDiagnosticSubmission(BaseModel):
    """A partner submits a diagnostic report via their exchange contract."""

    building_id: UUID
    diagnostic_type: str = Field(
        ...,
        pattern=r"^(asbestos|pcb|lead|hap|radon|pfas|multi|full)$",
        description="Pollutant type of the diagnostic report",
    )
    report_reference: str = Field(..., min_length=1, max_length=200)
    report_date: date
    document_id: UUID | None = None  # if document was already uploaded
    text_content: str | None = None  # OCR text for extraction
    metadata: dict = Field(default_factory=dict)


class PartnerQuoteSubmission(BaseModel):
    """A partner submits a quote for an open tender."""

    tender_id: UUID
    total_amount_chf: float = Field(..., gt=0)
    scope_description: str = Field(..., min_length=1)
    validity_date: date
    document_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class PartnerAcknowledgmentSubmission(BaseModel):
    """A partner acknowledges receipt of a transfer or pack."""

    envelope_id: UUID | None = None
    pack_id: UUID | None = None
    acknowledged: bool = True
    notes: str | None = None


class SubmissionReceipt(BaseModel):
    """Typed receipt returned after a partner submission."""

    model_config = ConfigDict(from_attributes=True)

    submission_id: UUID
    status: str  # accepted, pending_review, rejected
    contract_id: UUID
    conformance_result: dict | None = None
    timestamp: datetime
    next_steps: str


class PendingSubmissionRead(BaseModel):
    """A pending submission as returned by the listing endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID
    organization_id: UUID
    task_type: str
    target_type: str
    target_id: UUID
    title: str
    description: str | None = None
    priority: str
    status: str
    created_at: datetime | None = None
