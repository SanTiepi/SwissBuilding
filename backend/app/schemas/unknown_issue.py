import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UnknownIssueCreate(BaseModel):
    unknown_type: str
    severity: str = "medium"
    status: str = "open"
    title: str
    description: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    blocks_readiness: bool = False
    readiness_types_affected: str | None = None
    detected_by: str | None = None


class UnknownIssueUpdate(BaseModel):
    unknown_type: str | None = None
    severity: str | None = None
    status: str | None = None
    title: str | None = None
    description: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    blocks_readiness: bool | None = None
    readiness_types_affected: str | None = None
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    detected_by: str | None = None


class UnknownIssueRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    unknown_type: str
    severity: str
    status: str
    title: str
    description: str | None
    entity_type: str | None
    entity_id: uuid.UUID | None
    blocks_readiness: bool
    readiness_types_affected: str | None
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None
    detected_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
