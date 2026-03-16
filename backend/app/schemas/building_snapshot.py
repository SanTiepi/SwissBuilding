import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BuildingSnapshotCreate(BaseModel):
    snapshot_type: str = "manual"
    trigger_event: str | None = None
    notes: str | None = None


class BuildingSnapshotRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    snapshot_type: str
    trigger_event: str | None
    passport_state_json: dict | None
    trust_state_json: dict | None
    readiness_state_json: dict | None
    evidence_counts_json: dict | None
    passport_grade: str | None
    overall_trust: float | None
    completeness_score: float | None
    captured_at: datetime
    captured_by: uuid.UUID | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
