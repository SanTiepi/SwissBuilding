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
    identified_by_ai: bool = False
    ai_confidence: float | None = None
    year_estimated: int | None = None
    ai_pollutants: dict | None = None
    ai_recommendations: list[str] | None = None


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
    identified_by_ai: bool
    ai_confidence: float | None
    year_estimated: int | None
    ai_pollutants: dict | None
    ai_recommendations: list | None

    model_config = ConfigDict(from_attributes=True)
