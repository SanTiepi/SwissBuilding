import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ZoneCreate(BaseModel):
    zone_type: str
    name: str
    description: str | None = None
    floor_number: int | None = None
    surface_area_m2: float | None = None
    parent_zone_id: uuid.UUID | None = None


class ZoneUpdate(BaseModel):
    zone_type: str | None = None
    name: str | None = None
    description: str | None = None
    floor_number: int | None = None
    surface_area_m2: float | None = None
    parent_zone_id: uuid.UUID | None = None


class ZoneRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    parent_zone_id: uuid.UUID | None
    zone_type: str
    name: str
    description: str | None
    floor_number: int | None
    surface_area_m2: float | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None
    children_count: int = 0
    elements_count: int = 0

    model_config = ConfigDict(from_attributes=True)
