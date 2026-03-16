from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class TimelineLink(BaseModel):
    source_event_id: str
    target_event_id: str
    link_type: Literal["caused_by", "followed_by", "related_to", "triggered", "superseded_by"]

    model_config = ConfigDict(from_attributes=True)


class EnrichedTimelineEntry(BaseModel):
    id: str
    date: datetime
    event_type: str
    title: str
    description: str | None = None
    icon_hint: str
    metadata: dict[str, Any] | None = None
    source_id: str | None = None
    source_type: str | None = None
    links: list[TimelineLink] = []
    lifecycle_phase: Literal["discovery", "assessment", "remediation", "verification", "closed"] | None = None
    importance: Literal["low", "medium", "high", "critical"] = "low"

    model_config = ConfigDict(from_attributes=True)


class EnrichedTimeline(BaseModel):
    entries: list[EnrichedTimelineEntry]
    total: int
    links: list[TimelineLink] = []
    lifecycle_summary: dict[str, int] = {}
