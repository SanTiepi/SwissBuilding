"""Pydantic schemas for the InvalidationEvent model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InvalidationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID
    trigger_type: str
    trigger_id: UUID | None = None
    trigger_description: str
    affected_type: str
    affected_id: UUID
    impact_reason: str
    severity: str
    required_reaction: str
    status: str
    resolved_at: datetime | None = None
    resolved_by_id: UUID | None = None
    resolution_note: str | None = None
    detected_at: datetime | None = None
    created_at: datetime | None = None


class InvalidationResolveRequest(BaseModel):
    resolution_note: str


class InvalidationPendingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[InvalidationEventRead]
    total: int
