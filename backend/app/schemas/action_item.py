from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActionItemCreate(BaseModel):
    building_id: UUID | None = None
    diagnostic_id: UUID | None = None
    sample_id: UUID | None = None
    source_type: str = "manual"
    action_type: str
    title: str
    description: str | None = None
    priority: str = "medium"
    due_date: date | None = None
    assigned_to: UUID | None = None
    metadata_json: dict[str, Any] | None = None


class ActionItemUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None
    assigned_to: UUID | None = None
    title: str | None = None
    description: str | None = None
    metadata_json: dict[str, Any] | None = None


class ActionItemRead(BaseModel):
    id: UUID
    building_id: UUID
    diagnostic_id: UUID | None
    sample_id: UUID | None
    campaign_id: UUID | None
    source_type: str
    action_type: str
    title: str
    description: str | None
    priority: str
    status: str
    due_date: date | None
    assigned_to: UUID | None
    created_by: UUID | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
