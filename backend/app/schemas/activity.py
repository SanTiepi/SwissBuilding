from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityItemRead(BaseModel):
    id: UUID
    kind: str  # "diagnostic", "document", "event", "action"
    source_id: UUID
    building_id: UUID
    occurred_at: datetime
    title: str
    description: str | None = None
    status: str | None = None
    actor_id: UUID | None = None
    linked_object_type: str | None = None
    linked_object_id: UUID | None = None
    metadata_json: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
