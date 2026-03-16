import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TechnicalPlanCreate(BaseModel):
    plan_type: str
    title: str
    file_path: str
    file_name: str
    description: str | None = None
    floor_number: int | None = None
    version: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    zone_id: uuid.UUID | None = None


class TechnicalPlanRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    plan_type: str
    title: str
    description: str | None
    floor_number: int | None
    version: str | None
    file_path: str
    file_name: str
    mime_type: str | None
    file_size_bytes: int | None
    zone_id: uuid.UUID | None
    uploaded_by: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
