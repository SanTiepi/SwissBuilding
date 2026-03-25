"""BatiConnect — Exchange contract and publication schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- Exchange Contract Version ---


class ExchangeContractRead(BaseModel):
    id: UUID
    contract_code: str
    version: int
    status: str
    audience_type: str
    payload_type: str
    schema_reference: str | None
    effective_from: date
    effective_to: date | None
    compatibility_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Passport Publication ---


class PublicationCreate(BaseModel):
    contract_version_id: UUID
    audience_type: str
    publication_type: str
    pack_id: UUID | None = None
    content_hash: str
    delivery_state: str = "published"


class PublicationRead(BaseModel):
    id: UUID
    building_id: UUID
    contract_version_id: UUID
    audience_type: str
    publication_type: str
    pack_id: UUID | None
    content_hash: str
    published_at: datetime
    published_by_org_id: UUID | None
    published_by_user_id: UUID | None
    delivery_state: str
    superseded_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Import Receipt ---


class ImportReceiptCreate(BaseModel):
    building_id: UUID | None = None
    source_system: str
    contract_code: str
    contract_version: int
    import_reference: str | None = None
    content_hash: str
    status: str = "received"
    rejection_reason: str | None = None
    matched_publication_id: UUID | None = None
    notes: str | None = None


class ImportReceiptRead(BaseModel):
    id: UUID
    building_id: UUID | None
    source_system: str
    contract_code: str
    contract_version: int
    import_reference: str | None
    imported_at: datetime
    status: str
    content_hash: str
    rejection_reason: str | None
    matched_publication_id: UUID | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
