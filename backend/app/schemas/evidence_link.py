import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceLinkCreate(BaseModel):
    source_type: str
    source_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relationship: str
    confidence: float | None = None
    legal_reference: str | None = None
    explanation: str | None = None


class EvidenceLinkRead(BaseModel):
    id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relationship: str
    confidence: float | None
    legal_reference: str | None
    explanation: str | None
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
