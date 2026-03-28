"""Pydantic schemas for BuildingPassportEnvelope and PassportTransferReceipt."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


class PassportEnvelopeCreate(BaseModel):
    redaction_profile: str = "none"
    version_label: str | None = None


class PassportEnvelopeResponse(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    organization_id: uuid.UUID
    created_by_id: uuid.UUID

    version: int
    version_label: str | None

    passport_data: dict
    sections_included: list[str]

    content_hash: str

    redaction_profile: str | None
    financials_redacted: bool
    personal_data_redacted: bool

    is_sovereign: bool
    supersedes_id: uuid.UUID | None
    superseded_at: datetime | None

    status: str

    frozen_at: datetime | None
    frozen_by_id: uuid.UUID | None
    published_at: datetime | None
    published_by_id: uuid.UUID | None

    transferred_to_type: str | None
    transferred_to_id: uuid.UUID | None
    transferred_at: datetime | None
    transfer_method: str | None

    acknowledged_at: datetime | None
    acknowledged_by_id: uuid.UUID | None
    receipt_hash: str | None

    reimportable: bool
    reimport_format: str

    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PassportEnvelopeHistoryResponse(BaseModel):
    items: list[PassportEnvelopeResponse]
    count: int


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------


class PassportTransferRequest(BaseModel):
    recipient_type: str  # organization, person, authority
    recipient_id: uuid.UUID | None = None
    recipient_name: str | None = None
    delivery_method: str = "in_app"  # in_app, email, download, api, physical
    notes: str | None = None


class PassportTransferReceiptResponse(BaseModel):
    id: uuid.UUID
    envelope_id: uuid.UUID
    sender_org_id: uuid.UUID
    recipient_org_id: uuid.UUID | None
    recipient_name: str | None

    sent_at: datetime
    delivery_method: str
    delivery_proof_hash: str

    acknowledged: bool
    acknowledged_at: datetime | None
    acknowledged_by_name: str | None
    receipt_hash: str | None

    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Acknowledge
# ---------------------------------------------------------------------------


class PassportAcknowledgeRequest(BaseModel):
    acknowledged_by_name: str
    receipt_hash: str | None = None


# ---------------------------------------------------------------------------
# Supersede
# ---------------------------------------------------------------------------


class PassportSupersedeRequest(BaseModel):
    reason: str | None = None


# ---------------------------------------------------------------------------
# Re-import
# ---------------------------------------------------------------------------


class PassportReimportRequest(BaseModel):
    envelope_data: dict
