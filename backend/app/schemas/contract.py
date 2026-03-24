from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContractCreate(BaseModel):
    building_id: UUID | None = None
    contract_type: str  # maintenance | management_mandate | concierge | cleaning | elevator | heating | insurance | security | energy | other
    reference_code: str
    title: str
    counterparty_type: str  # contact | user | organization
    counterparty_id: UUID
    date_start: date
    date_end: date | None = None
    annual_cost_chf: float | None = None
    payment_frequency: str | None = None  # monthly | quarterly | semi_annual | annual
    auto_renewal: bool = False
    notice_period_months: int | None = None
    status: str = "active"
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class ContractUpdate(BaseModel):
    contract_type: str | None = None
    reference_code: str | None = None
    title: str | None = None
    counterparty_type: str | None = None
    counterparty_id: UUID | None = None
    date_start: date | None = None
    date_end: date | None = None
    annual_cost_chf: float | None = None
    payment_frequency: str | None = None
    auto_renewal: bool | None = None
    notice_period_months: int | None = None
    status: str | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class ContractRead(BaseModel):
    id: UUID
    building_id: UUID
    contract_type: str
    reference_code: str
    title: str
    counterparty_type: str
    counterparty_id: UUID
    date_start: date
    date_end: date | None
    annual_cost_chf: float | None
    payment_frequency: str | None
    auto_renewal: bool
    notice_period_months: int | None
    status: str
    notes: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    counterparty_display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ContractListRead(BaseModel):
    id: UUID
    building_id: UUID
    contract_type: str
    reference_code: str
    title: str
    counterparty_type: str
    date_start: date
    date_end: date | None
    annual_cost_chf: float | None
    status: str
    counterparty_display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
