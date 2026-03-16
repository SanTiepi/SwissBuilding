import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PostWorksStateCreate(BaseModel):
    intervention_id: uuid.UUID | None = None
    state_type: str
    pollutant_type: str | None = None
    title: str
    description: str | None = None
    zone_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    material_id: uuid.UUID | None = None
    verified: bool = False
    evidence_json: str | None = None
    notes: str | None = None


class PostWorksStateUpdate(BaseModel):
    intervention_id: uuid.UUID | None = None
    state_type: str | None = None
    pollutant_type: str | None = None
    title: str | None = None
    description: str | None = None
    zone_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    material_id: uuid.UUID | None = None
    verified: bool | None = None
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    evidence_json: str | None = None
    notes: str | None = None


class PostWorksStateRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    intervention_id: uuid.UUID | None
    state_type: str
    pollutant_type: str | None
    title: str
    description: str | None
    zone_id: uuid.UUID | None
    element_id: uuid.UUID | None
    material_id: uuid.UUID | None
    verified: bool
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    evidence_json: str | None
    recorded_by: uuid.UUID | None
    recorded_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
