from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaxContextCreate(BaseModel):
    building_id: UUID
    tax_type: str  # property_tax | impot_foncier | valeur_locative | tax_estimation
    fiscal_year: int
    official_value_chf: float | None = None
    taxable_value_chf: float | None = None
    tax_amount_chf: float | None = None
    canton: str
    municipality: str | None = None
    status: str = "estimated"  # estimated | assessed | contested | final
    assessment_date: date | None = None
    document_id: UUID | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class TaxContextUpdate(BaseModel):
    tax_type: str | None = None
    fiscal_year: int | None = None
    official_value_chf: float | None = None
    taxable_value_chf: float | None = None
    tax_amount_chf: float | None = None
    canton: str | None = None
    municipality: str | None = None
    status: str | None = None
    assessment_date: date | None = None
    document_id: UUID | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class TaxContextRead(BaseModel):
    id: UUID
    building_id: UUID
    tax_type: str
    fiscal_year: int
    official_value_chf: float | None
    taxable_value_chf: float | None
    tax_amount_chf: float | None
    canton: str
    municipality: str | None
    status: str
    assessment_date: date | None
    document_id: UUID | None
    notes: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxContextListRead(BaseModel):
    id: UUID
    building_id: UUID
    tax_type: str
    fiscal_year: int
    tax_amount_chf: float | None
    canton: str
    status: str

    model_config = ConfigDict(from_attributes=True)
