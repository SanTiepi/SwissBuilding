"""BatiConnect — Mise en concurrence encadree: RFQ schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# TenderRequest
# ---------------------------------------------------------------------------


class TenderRequestCreate(BaseModel):
    building_id: UUID
    title: str
    description: str | None = None
    work_type: str  # asbestos_removal | pcb_removal | lead_removal | hap_removal | radon_mitigation | pfas_remediation | multi_pollutant | other
    deadline_submission: datetime | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    attachments_manual: list[str] | None = None


class TenderRequestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    work_type: str | None = None
    deadline_submission: datetime | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    attachments_manual: list[str] | None = None
    status: str | None = None


class TenderRequestRead(BaseModel):
    id: UUID
    building_id: UUID
    organization_id: UUID | None
    created_by_id: UUID
    title: str
    description: str | None
    scope_summary: str | None
    work_type: str
    deadline_submission: datetime | None
    planned_start_date: date | None
    planned_end_date: date | None
    status: str
    attachments_auto: list | None
    attachments_manual: list | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# TenderInvitation
# ---------------------------------------------------------------------------


class TenderInvitationCreate(BaseModel):
    contractor_org_ids: list[UUID]


class TenderInvitationRead(BaseModel):
    id: UUID
    tender_id: UUID
    contractor_org_id: UUID
    sent_at: datetime | None
    viewed_at: datetime | None
    responded_at: datetime | None
    status: str
    access_token: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# TenderQuote
# ---------------------------------------------------------------------------


class TenderQuoteCreate(BaseModel):
    invitation_id: UUID | None = None
    contractor_org_id: UUID
    total_amount_chf: Decimal | None = None
    currency: str = "CHF"
    scope_description: str | None = None
    exclusions: str | None = None
    inclusions: str | None = None
    estimated_duration_days: int | None = None
    validity_date: date | None = None
    document_id: UUID | None = None


class TenderQuoteRead(BaseModel):
    id: UUID
    tender_id: UUID
    invitation_id: UUID | None
    contractor_org_id: UUID
    total_amount_chf: Decimal | None
    currency: str
    scope_description: str | None
    exclusions: str | None
    inclusions: str | None
    estimated_duration_days: int | None
    validity_date: date | None
    document_id: UUID | None
    extracted_data: dict | None
    status: str
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# TenderComparison
# ---------------------------------------------------------------------------


class TenderComparisonRead(BaseModel):
    id: UUID
    tender_id: UUID
    created_by_id: UUID
    comparison_data: dict | None
    selected_quote_id: UUID | None
    selection_reason: str | None
    attributed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Attribution request body
# ---------------------------------------------------------------------------


class TenderAttributeRequest(BaseModel):
    quote_id: UUID
    reason: str | None = None
