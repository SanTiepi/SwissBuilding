import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BuildingElementCreate(BaseModel):
    element_type: str
    name: str
    description: str | None = None
    condition: str | None = None
    installation_year: int | None = None


class BuildingElementUpdate(BaseModel):
    element_type: str | None = None
    name: str | None = None
    description: str | None = None
    condition: str | None = None
    installation_year: int | None = None


class BuildingElementRead(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    element_type: str
    name: str
    description: str | None
    condition: str | None
    installation_year: int | None
    last_inspected_at: datetime | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None
    materials_count: int = 0

    model_config = ConfigDict(from_attributes=True)
