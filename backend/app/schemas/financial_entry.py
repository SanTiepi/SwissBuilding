from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FinancialEntryCreate(BaseModel):
    building_id: UUID
    entry_type: str  # expense | income
    category: str
    amount_chf: float
    entry_date: date
    period_start: date | None = None
    period_end: date | None = None
    fiscal_year: int | None = None
    description: str | None = None
    contract_id: UUID | None = None
    lease_id: UUID | None = None
    intervention_id: UUID | None = None
    insurance_policy_id: UUID | None = None
    document_id: UUID | None = None
    external_ref: str | None = None
    status: str = "recorded"
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class FinancialEntryUpdate(BaseModel):
    entry_type: str | None = None
    category: str | None = None
    amount_chf: float | None = None
    entry_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    fiscal_year: int | None = None
    description: str | None = None
    contract_id: UUID | None = None
    lease_id: UUID | None = None
    intervention_id: UUID | None = None
    insurance_policy_id: UUID | None = None
    document_id: UUID | None = None
    external_ref: str | None = None
    status: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class FinancialEntryRead(BaseModel):
    id: UUID
    building_id: UUID
    entry_type: str
    category: str
    amount_chf: float
    entry_date: date
    period_start: date | None
    period_end: date | None
    fiscal_year: int | None
    description: str | None
    contract_id: UUID | None
    lease_id: UUID | None
    intervention_id: UUID | None
    insurance_policy_id: UUID | None
    document_id: UUID | None
    external_ref: str | None
    status: str
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialEntryListRead(BaseModel):
    id: UUID
    building_id: UUID
    entry_type: str
    category: str
    amount_chf: float
    entry_date: date
    fiscal_year: int | None
    status: str

    model_config = ConfigDict(from_attributes=True)
