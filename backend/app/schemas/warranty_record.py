"""BatiConnect — WarrantyRecord schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WarrantyRecordCreate(BaseModel):
    warranty_type: str  # works | equipment | material | system | waterproofing | roof | facade | structural | other
    subject: str
    provider_name: str
    case_id: UUID | None = None
    start_date: date
    end_date: date
    duration_months: int | None = None
    coverage_description: str | None = None
    exclusions: str | None = None
    conditions: str | None = None
    document_id: UUID | None = None
    status: str = "active"
    notes: str | None = None


class WarrantyRecordUpdate(BaseModel):
    warranty_type: str | None = None
    subject: str | None = None
    provider_name: str | None = None
    case_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_months: int | None = None
    coverage_description: str | None = None
    exclusions: str | None = None
    conditions: str | None = None
    document_id: UUID | None = None
    status: str | None = None
    claim_filed: bool | None = None
    claim_date: date | None = None
    claim_description: str | None = None
    notes: str | None = None


class WarrantyRecordRead(BaseModel):
    id: UUID
    building_id: UUID
    case_id: UUID | None
    organization_id: UUID
    warranty_type: str
    subject: str
    provider_name: str
    start_date: date
    end_date: date
    duration_months: int | None
    coverage_description: str | None
    exclusions: str | None
    conditions: str | None
    document_id: UUID | None
    status: str
    claim_filed: bool
    claim_date: date | None
    claim_description: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
