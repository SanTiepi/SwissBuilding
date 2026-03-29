"""Schemas for the Building Activity Ledger."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BuildingActivityRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    actor_id: uuid.UUID
    actor_role: str
    actor_name: str
    activity_type: str
    entity_type: str
    entity_id: uuid.UUID
    title: str
    description: str | None
    reason: str | None
    metadata_json: dict | None
    previous_hash: str | None
    activity_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingActivityListRead(BaseModel):
    items: list[BuildingActivityRead]
    total: int
    page: int
    size: int


class ChainIntegrityRead(BaseModel):
    valid: bool
    total_entries: int
    first_break_at: int | None
