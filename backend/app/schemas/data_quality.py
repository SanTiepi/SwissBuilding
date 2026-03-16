import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DataQualityIssueCreate(BaseModel):
    issue_type: str
    severity: str = "medium"
    status: str = "open"
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    field_name: str | None = None
    description: str
    suggestion: str | None = None
    detected_by: str | None = None


class DataQualityIssueUpdate(BaseModel):
    issue_type: str | None = None
    severity: str | None = None
    status: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    field_name: str | None = None
    description: str | None = None
    suggestion: str | None = None
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    detected_by: str | None = None


class DataQualityIssueRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    issue_type: str
    severity: str
    status: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    field_name: str | None
    description: str
    suggestion: str | None
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None
    detected_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
