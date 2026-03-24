from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OwnershipRecordCreate(BaseModel):
    building_id: UUID | None = None  # optional: path param takes precedence
    owner_type: str  # contact | user | organization
    owner_id: UUID
    share_pct: float | None = None
    ownership_type: str  # full | co_ownership | usufruct | bare_ownership | ppe_unit
    acquisition_type: str | None = None  # purchase | inheritance | donation | construction | exchange
    acquisition_date: date | None = None
    disposal_date: date | None = None
    acquisition_price_chf: float | None = None
    land_register_ref: str | None = None
    status: str = "active"  # active | transferred | disputed | archived
    document_id: UUID | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class OwnershipRecordUpdate(BaseModel):
    share_pct: float | None = None
    ownership_type: str | None = None
    acquisition_type: str | None = None
    acquisition_date: date | None = None
    disposal_date: date | None = None
    acquisition_price_chf: float | None = None
    land_register_ref: str | None = None
    status: str | None = None
    document_id: UUID | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class OwnershipRecordRead(BaseModel):
    id: UUID
    building_id: UUID
    owner_type: str
    owner_id: UUID
    share_pct: float | None
    ownership_type: str
    acquisition_type: str | None
    acquisition_date: date | None
    disposal_date: date | None
    acquisition_price_chf: float | None
    land_register_ref: str | None
    status: str
    document_id: UUID | None
    notes: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    owner_display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OwnershipRecordListRead(BaseModel):
    id: UUID
    building_id: UUID
    owner_type: str
    owner_id: UUID
    share_pct: float | None
    ownership_type: str
    status: str
    acquisition_date: date | None
    owner_display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
