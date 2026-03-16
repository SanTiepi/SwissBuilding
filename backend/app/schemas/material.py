import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialCreate(BaseModel):
    material_type: str
    name: str
    description: str | None = None
    manufacturer: str | None = None
    installation_year: int | None = None
    contains_pollutant: bool = False
    pollutant_type: str | None = None
    pollutant_confirmed: bool = False
    sample_id: uuid.UUID | None = None
    source: str | None = None
    notes: str | None = None


class MaterialRead(BaseModel):
    id: uuid.UUID
    element_id: uuid.UUID
    material_type: str
    name: str
    description: str | None
    manufacturer: str | None
    installation_year: int | None
    contains_pollutant: bool
    pollutant_type: str | None
    pollutant_confirmed: bool
    sample_id: uuid.UUID | None
    source: str | None
    notes: str | None
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
