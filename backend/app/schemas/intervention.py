import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class InterventionCreate(BaseModel):
    intervention_type: str
    title: str
    description: str | None = None
    status: str = "completed"
    date_start: date | None = None
    date_end: date | None = None
    contractor_name: str | None = None
    contractor_id: uuid.UUID | None = None
    cost_chf: float | None = None
    zones_affected: list[str] | None = None
    materials_used: list[str] | None = None
    diagnostic_id: uuid.UUID | None = None
    notes: str | None = None


class InterventionUpdate(BaseModel):
    intervention_type: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    date_start: date | None = None
    date_end: date | None = None
    contractor_name: str | None = None
    contractor_id: uuid.UUID | None = None
    cost_chf: float | None = None
    zones_affected: list[str] | None = None
    materials_used: list[str] | None = None
    diagnostic_id: uuid.UUID | None = None
    notes: str | None = None


class InterventionRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    intervention_type: str
    title: str
    description: str | None
    status: str
    date_start: date | None
    date_end: date | None
    contractor_name: str | None
    contractor_id: uuid.UUID | None
    cost_chf: float | None
    zones_affected: list[str] | None
    materials_used: list[str] | None
    diagnostic_id: uuid.UUID | None
    notes: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
