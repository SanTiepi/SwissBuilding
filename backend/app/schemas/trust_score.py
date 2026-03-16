import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BuildingTrustScoreCreate(BaseModel):
    overall_score: float
    percent_proven: float | None = None
    percent_inferred: float | None = None
    percent_declared: float | None = None
    percent_obsolete: float | None = None
    percent_contradictory: float | None = None
    total_data_points: int = 0
    proven_count: int = 0
    inferred_count: int = 0
    declared_count: int = 0
    obsolete_count: int = 0
    contradictory_count: int = 0
    trend: str | None = None
    previous_score: float | None = None
    assessed_by: str | None = None
    notes: str | None = None


class BuildingTrustScoreUpdate(BaseModel):
    overall_score: float | None = None
    percent_proven: float | None = None
    percent_inferred: float | None = None
    percent_declared: float | None = None
    percent_obsolete: float | None = None
    percent_contradictory: float | None = None
    total_data_points: int | None = None
    proven_count: int | None = None
    inferred_count: int | None = None
    declared_count: int | None = None
    obsolete_count: int | None = None
    contradictory_count: int | None = None
    trend: str | None = None
    previous_score: float | None = None
    assessed_by: str | None = None
    notes: str | None = None


class BuildingTrustScoreRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    overall_score: float
    percent_proven: float | None
    percent_inferred: float | None
    percent_declared: float | None
    percent_obsolete: float | None
    percent_contradictory: float | None
    total_data_points: int
    proven_count: int
    inferred_count: int
    declared_count: int
    obsolete_count: int
    contradictory_count: int
    trend: str | None
    previous_score: float | None
    assessed_at: datetime
    assessed_by: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
