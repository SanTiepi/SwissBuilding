"""Pydantic schemas for the Building Change Grammar (Observation, Event, Delta, Signal)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------


class BuildingObservationCreate(BaseModel):
    observation_type: str = Field(..., description="measurement, inspection, assessment, reading, survey")
    observer_role: str = Field(..., description="diagnostician, owner, contractor, authority, system")
    observed_at: datetime | None = None
    case_id: uuid.UUID | None = None

    target_type: str = Field(..., description="zone, element, material, system, building")
    target_id: uuid.UUID | None = None
    subject: str
    value: str
    unit: str | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    method: str = "visual"

    source_document_id: uuid.UUID | None = None
    source_extraction_id: uuid.UUID | None = None
    notes: str | None = None


class BuildingObservationRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    case_id: uuid.UUID | None
    observation_type: str
    observer_id: uuid.UUID
    observer_role: str
    observed_at: datetime
    target_type: str
    target_id: uuid.UUID | None
    subject: str
    value: str
    unit: str | None
    confidence: float | None
    method: str
    source_document_id: uuid.UUID | None
    source_extraction_id: uuid.UUID | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class BuildingEventCreate(BaseModel):
    event_type: str
    occurred_at: datetime | None = None
    title: str
    description: str | None = None
    case_id: uuid.UUID | None = None
    impact_scope: str | None = None
    impact_target_id: uuid.UUID | None = None
    impact_description: str | None = None
    severity: str = "info"
    source_type: str | None = None
    source_id: uuid.UUID | None = None


class BuildingEventRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    case_id: uuid.UUID | None
    event_type: str
    occurred_at: datetime
    title: str
    description: str | None
    actor_id: uuid.UUID | None
    impact_scope: str | None
    impact_target_id: uuid.UUID | None
    impact_description: str | None
    severity: str
    source_type: str | None
    source_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Delta
# ---------------------------------------------------------------------------


class BuildingDeltaCompute(BaseModel):
    delta_type: str
    period_start: datetime
    period_end: datetime


class BuildingDeltaRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    delta_type: str
    computed_at: datetime
    period_start: datetime
    period_end: datetime
    before_value: str
    after_value: str
    before_snapshot_id: uuid.UUID | None
    after_snapshot_id: uuid.UUID | None
    direction: str
    magnitude: str
    explanation: str | None
    triggered_by_event_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------


class BuildingSignalRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    signal_type: str
    detected_at: datetime
    severity: str
    confidence: float | None
    title: str
    description: str
    recommended_action: str | None
    based_on_type: str
    based_on_ids: list[Any] | None
    status: str
    resolved_at: datetime | None
    resolved_by_id: uuid.UUID | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SignalResolveRequest(BaseModel):
    resolution_note: str | None = None


# ---------------------------------------------------------------------------
# Unified change timeline entry
# ---------------------------------------------------------------------------


class ChangeTimelineEntry(BaseModel):
    id: uuid.UUID
    change_type: str  # observation, event, delta, signal
    occurred_at: datetime
    title: str
    description: str | None = None
    severity: str | None = None
    metadata: dict[str, Any] | None = None
