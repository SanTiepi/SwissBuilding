"""ControlTower v2 — Action Feed read-model schemas."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ActionFeedItem(BaseModel):
    id: str  # composite key: "{source_type}:{source_id}"
    priority: int  # 0-4
    priority_label: (
        str  # procedural_blocker|overdue_authority_request|overdue_obligation|pending_review|upcoming_deadline
    )
    source_type: str  # obligation|procedure|authority_request|inbox|publication|intake|lease|contract
    source_id: UUID
    building_id: UUID | None = None
    building_address: str | None = None
    title: str
    description: str
    due_date: date | None = None
    assigned_org_id: UUID | None = None
    assigned_user_id: UUID | None = None
    link: str  # frontend route hint
    confidence_level: str | None = None
    freshness_state: str | None = None


class ActionFeedResponse(BaseModel):
    items: list[ActionFeedItem]
    total: int
    filters_applied: dict


class ActionFeedSummary(BaseModel):
    total: int
    by_priority: dict[int, int]  # {0: count, 1: count, ...}
    by_source_type: dict[str, int]
