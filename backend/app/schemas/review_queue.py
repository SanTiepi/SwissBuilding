from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReviewTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID
    organization_id: UUID
    task_type: str
    target_type: str
    target_id: UUID
    title: str
    description: str | None = None
    case_id: UUID | None = None
    priority: str
    assigned_to_id: UUID | None = None
    status: str
    completed_at: datetime | None = None
    completed_by_id: UUID | None = None
    resolution: str | None = None
    resolution_note: str | None = None
    escalation_reason: str | None = None
    escalated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReviewTaskAssign(BaseModel):
    assigned_to_id: UUID


class ReviewTaskComplete(BaseModel):
    resolution: str  # approved, rejected, corrected, escalated
    resolution_note: str | None = None


class ReviewTaskEscalate(BaseModel):
    escalation_reason: str


class ReviewQueueStats(BaseModel):
    total_pending: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    by_type: dict[str, int] = {}
    overdue_7d: int = 0
