import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FieldObservationCreate(BaseModel):
    building_id: uuid.UUID | None = None
    observation_type: str
    severity: str = "info"
    title: str
    description: str | None = None
    zone_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    location_description: str | None = None
    observed_at: datetime | None = None
    photo_reference: str | None = None
    metadata_json: str | None = None
    observer_role: str | None = None
    tags: list[str] | None = None
    context_json: dict | None = None
    confidence: str = "likely"


class FieldObservationUpdate(BaseModel):
    observation_type: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None
    zone_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    location_description: str | None = None
    observed_at: datetime | None = None
    photo_reference: str | None = None
    metadata_json: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    context_json: dict | None = None
    confidence: str | None = None


class FieldObservationRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID | None
    zone_id: uuid.UUID | None
    element_id: uuid.UUID | None
    observer_id: uuid.UUID
    observer_role: str | None
    observation_type: str
    severity: str
    title: str
    description: str | None
    location_description: str | None
    observed_at: datetime | None
    photo_reference: str | None
    verified: bool
    verified_by_id: uuid.UUID | None
    verified_at: datetime | None
    metadata_json: str | None
    status: str
    tags: str | None
    context_json: str | None
    confidence: str
    upvotes: int
    is_verified: bool
    created_at: datetime | None
    updated_at: datetime | None
    observer_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FieldObservationListRead(BaseModel):
    items: list[FieldObservationRead]
    total: int
    page: int
    size: int
    pages: int


class FieldObservationSummary(BaseModel):
    building_id: uuid.UUID
    total_observations: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    unverified_count: int
    latest_observation_at: datetime | None


class FieldObservationVerify(BaseModel):
    verified: bool
    notes: str | None = None


class PatternInsightRead(BaseModel):
    pattern: str
    occurrences: int
    confidence: str
    buildings_count: int
    recommendation: str
    tags: list[str]

    model_config = ConfigDict(from_attributes=True)
