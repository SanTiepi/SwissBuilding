from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TimelineEntryRead(BaseModel):
    id: str
    date: datetime
    event_type: str  # "construction", "diagnostic", "sample", "document", "intervention", "risk_change", "plan", "event", "diagnostic_publication"
    title: str
    description: str | None = None
    icon_hint: str  # "building", "microscope", "flask", "file", "wrench", "shield", "map", "calendar"
    metadata: dict[str, Any] | None = None
    source_id: str | None = None
    source_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TimelineResponse(BaseModel):
    items: list[TimelineEntryRead]
    total: int
    page: int
    size: int
    pages: int
