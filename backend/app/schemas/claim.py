from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClaimCreate(BaseModel):
    insurance_policy_id: UUID
    building_id: UUID
    claim_type: str  # water_damage | fire | natural_hazard | liability | theft | pollutant_related | other
    reference_number: str | None = None
    status: str = "open"
    incident_date: date
    description: str | None = None
    claimed_amount_chf: float | None = None
    approved_amount_chf: float | None = None
    paid_amount_chf: float | None = None
    zone_id: UUID | None = None
    intervention_id: UUID | None = None
    notes: str | None = None


class ClaimUpdate(BaseModel):
    claim_type: str | None = None
    reference_number: str | None = None
    status: str | None = None
    incident_date: date | None = None
    description: str | None = None
    claimed_amount_chf: float | None = None
    approved_amount_chf: float | None = None
    paid_amount_chf: float | None = None
    zone_id: UUID | None = None
    intervention_id: UUID | None = None
    notes: str | None = None


class ClaimRead(BaseModel):
    id: UUID
    insurance_policy_id: UUID
    building_id: UUID
    claim_type: str
    reference_number: str | None
    status: str
    incident_date: date
    description: str | None
    claimed_amount_chf: float | None
    approved_amount_chf: float | None
    paid_amount_chf: float | None
    zone_id: UUID | None
    intervention_id: UUID | None
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimListRead(BaseModel):
    id: UUID
    insurance_policy_id: UUID
    building_id: UUID
    claim_type: str
    reference_number: str | None
    status: str
    incident_date: date
    claimed_amount_chf: float | None
    approved_amount_chf: float | None

    model_config = ConfigDict(from_attributes=True)
