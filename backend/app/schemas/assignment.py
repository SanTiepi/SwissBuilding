from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    target_type: str  # building, diagnostic
    target_id: UUID
    user_id: UUID
    role: str  # responsible, owner_contact, diagnostician, reviewer, contractor_contact


class AssignmentRead(BaseModel):
    id: UUID
    target_type: str
    target_id: UUID
    user_id: UUID
    role: str
    created_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
