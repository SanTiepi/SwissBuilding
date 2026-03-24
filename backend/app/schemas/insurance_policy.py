from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InsurancePolicyCreate(BaseModel):
    building_id: UUID
    contract_id: UUID | None = None
    policy_type: (
        str  # building_eca | rc_owner | rc_building | natural_hazard | construction_risk | complementary | contents
    )
    policy_number: str
    insurer_name: str
    insurer_contact_id: UUID | None = None
    insured_value_chf: float | None = None
    premium_annual_chf: float | None = None
    deductible_chf: float | None = None
    coverage_details_json: dict | None = None
    date_start: date
    date_end: date | None = None
    status: str = "active"
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class InsurancePolicyUpdate(BaseModel):
    contract_id: UUID | None = None
    policy_type: str | None = None
    policy_number: str | None = None
    insurer_name: str | None = None
    insurer_contact_id: UUID | None = None
    insured_value_chf: float | None = None
    premium_annual_chf: float | None = None
    deductible_chf: float | None = None
    coverage_details_json: dict | None = None
    date_start: date | None = None
    date_end: date | None = None
    status: str | None = None
    notes: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class InsurancePolicyRead(BaseModel):
    id: UUID
    building_id: UUID
    contract_id: UUID | None
    policy_type: str
    policy_number: str
    insurer_name: str
    insurer_contact_id: UUID | None
    insured_value_chf: float | None
    premium_annual_chf: float | None
    deductible_chf: float | None
    coverage_details_json: dict | None
    date_start: date
    date_end: date | None
    status: str
    notes: str | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InsurancePolicyListRead(BaseModel):
    id: UUID
    building_id: UUID
    policy_type: str
    policy_number: str
    insurer_name: str
    premium_annual_chf: float | None
    date_start: date
    date_end: date | None
    status: str

    model_config = ConfigDict(from_attributes=True)
