"""BatiConnect — Marketplace RFQ schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# ClientRequest
# ---------------------------------------------------------------------------


class ClientRequestCreate(BaseModel):
    building_id: UUID
    title: str
    description: str | None = None
    pollutant_types: list[str] | None = None
    work_category: str  # minor | medium | major
    estimated_area_m2: float | None = None
    deadline: date | None = None
    diagnostic_publication_id: UUID | None = None
    budget_indication: str | None = None
    site_access_notes: str | None = None


class ClientRequestPublish(BaseModel):
    diagnostic_publication_id: UUID | None = None


class ClientRequestRead(BaseModel):
    id: UUID
    building_id: UUID
    requester_user_id: UUID
    requester_org_id: UUID | None
    title: str
    description: str | None
    pollutant_types: list[str] | None
    work_category: str
    estimated_area_m2: float | None
    deadline: date | None
    status: str
    diagnostic_publication_id: UUID | None
    budget_indication: str | None
    site_access_notes: str | None
    published_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# RequestDocument
# ---------------------------------------------------------------------------


class RequestDocumentCreate(BaseModel):
    document_id: UUID | None = None
    filename: str
    file_url: str | None = None
    document_type: str  # specification | plan | diagnostic_report | photo | permit | other
    notes: str | None = None


class RequestDocumentRead(BaseModel):
    id: UUID
    client_request_id: UUID
    document_id: UUID | None
    filename: str
    file_url: str | None
    document_type: str
    uploaded_by_user_id: UUID | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# RequestInvitation
# ---------------------------------------------------------------------------


class RequestInvitationCreate(BaseModel):
    company_profile_ids: list[UUID]


class RequestInvitationRead(BaseModel):
    id: UUID
    client_request_id: UUID
    company_profile_id: UUID
    status: str
    sent_at: datetime
    viewed_at: datetime | None
    responded_at: datetime | None
    decline_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------


class QuoteCreate(BaseModel):
    client_request_id: UUID
    company_profile_id: UUID
    invitation_id: UUID | None = None
    amount_chf: Decimal
    currency: str = "CHF"
    validity_days: int = 30
    description: str | None = None
    work_plan: str | None = None
    timeline_weeks: int | None = None
    includes: list[str] | None = None
    excludes: list[str] | None = None


class QuoteSubmit(BaseModel):
    """Empty body — submission is an action, not a data update."""

    pass


class QuoteRead(BaseModel):
    id: UUID
    client_request_id: UUID
    company_profile_id: UUID
    invitation_id: UUID | None
    amount_chf: Decimal
    currency: str
    validity_days: int
    description: str | None
    work_plan: str | None
    timeline_weeks: int | None
    includes: list[str] | None
    excludes: list[str] | None
    status: str
    submitted_at: datetime | None
    content_hash: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# QuoteComparisonView — neutral listing
# ---------------------------------------------------------------------------


class QuoteComparisonEntry(BaseModel):
    quote_id: UUID
    company_name: str
    amount_chf: Decimal
    timeline_weeks: int | None
    includes: list[str] | None
    excludes: list[str] | None
    submitted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class QuoteComparisonView(BaseModel):
    client_request_id: UUID
    quotes: list[QuoteComparisonEntry]
