# COMPATIBILITY SURFACE — ChangeSignal is frozen per ADR-004.
# Canonical change objects are in building_change.py (BuildingSignal).
# No new semantics should be added here.

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChangeSignalCreate(BaseModel):
    signal_type: str
    severity: str = "info"
    status: str = "active"
    title: str
    description: str | None = None
    source: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    metadata_json: dict[str, Any] | None = None


class ChangeSignalUpdate(BaseModel):
    signal_type: str | None = None
    severity: str | None = None
    status: str | None = None
    title: str | None = None
    description: str | None = None
    source: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    metadata_json: dict[str, Any] | None = None
    acknowledged_by: uuid.UUID | None = None
    acknowledged_at: datetime | None = None


class ChangeSignalRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    signal_type: str
    severity: str
    status: str
    title: str
    description: str | None
    source: str | None
    entity_type: str | None
    entity_id: uuid.UUID | None
    metadata_json: dict[str, Any] | None
    detected_at: datetime
    acknowledged_by: uuid.UUID | None
    acknowledged_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
