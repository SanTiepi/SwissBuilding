from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeaseCreate(BaseModel):
    building_id: UUID | None = None  # optional: path param takes precedence
    unit_id: UUID | None = None
    zone_id: UUID | None = None
    lease_type: str  # residential | commercial | mixed | parking | storage | short_term
    reference_code: str
    tenant_type: str  # contact | user | organization
    tenant_id: UUID
    date_start: date
    date_end: date | None = None
    notice_period_months: int | None = None
    rent_monthly_chf: float | None = None
    charges_monthly_chf: float | None = None
    deposit_chf: float | None = None
    surface_m2: float | None = None
    rooms: float | None = None
    status: str = "active"
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class LeaseUpdate(BaseModel):
    unit_id: UUID | None = None
    zone_id: UUID | None = None
    lease_type: str | None = None
    reference_code: str | None = None
    date_start: date | None = None
    date_end: date | None = None
    notice_period_months: int | None = None
    rent_monthly_chf: float | None = None
    charges_monthly_chf: float | None = None
    deposit_chf: float | None = None
    surface_m2: float | None = None
    rooms: float | None = None
    status: str | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class LeaseRead(BaseModel):
    id: UUID
    building_id: UUID
    unit_id: UUID | None
    zone_id: UUID | None
    lease_type: str
    reference_code: str
    tenant_type: str
    tenant_id: UUID
    date_start: date
    date_end: date | None
    notice_period_months: int | None
    rent_monthly_chf: float | None
    charges_monthly_chf: float | None
    deposit_chf: float | None
    surface_m2: float | None
    rooms: float | None
    status: str
    notes: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    # Display fields (populated by service, not stored in DB)
    tenant_display_name: str | None = None
    unit_label: str | None = None
    zone_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LeaseListRead(BaseModel):
    id: UUID
    building_id: UUID
    lease_type: str
    reference_code: str
    tenant_type: str
    tenant_id: UUID
    date_start: date
    date_end: date | None
    rent_monthly_chf: float | None
    status: str

    # Display fields
    tenant_display_name: str | None = None
    unit_label: str | None = None
    zone_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LeaseEventCreate(BaseModel):
    lease_id: UUID
    event_type: str  # creation | renewal | rent_adjustment | notice_sent | notice_received | termination | dispute | deposit_return
    event_date: date
    description: str | None = None
    old_value_json: dict | None = None
    new_value_json: dict | None = None
    document_id: UUID | None = None


class LeaseEventRead(BaseModel):
    id: UUID
    lease_id: UUID
    event_type: str
    event_date: date
    description: str | None
    old_value_json: dict | None
    new_value_json: dict | None
    document_id: UUID | None
    created_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
