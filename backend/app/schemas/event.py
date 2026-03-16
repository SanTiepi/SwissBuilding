from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    event_type: str
    date: date
    title: str
    description: str | None = None
    metadata_json: dict[str, Any] | None = None


class EventRead(BaseModel):
    id: UUID
    building_id: UUID
    event_type: str
    date: date
    title: str
    description: str | None
    created_by: UUID | None
    metadata_json: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
