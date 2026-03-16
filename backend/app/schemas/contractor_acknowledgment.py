import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContractorAcknowledgmentCreate(BaseModel):
    intervention_id: uuid.UUID
    contractor_user_id: uuid.UUID
    safety_requirements: list[dict]
    expires_at: datetime | None = None


class ContractorAcknowledgmentResponse(BaseModel):
    id: uuid.UUID
    intervention_id: uuid.UUID
    building_id: uuid.UUID
    contractor_user_id: uuid.UUID
    status: str
    sent_at: datetime | None
    viewed_at: datetime | None
    acknowledged_at: datetime | None
    refused_at: datetime | None
    expires_at: datetime | None
    safety_requirements: list[dict]
    contractor_notes: str | None
    refusal_reason: str | None
    acknowledgment_hash: str | None
    ip_address: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ContractorAcknowledgmentAck(BaseModel):
    contractor_notes: str | None = None


class ContractorAcknowledgmentRefuse(BaseModel):
    refusal_reason: str


class ContractorAcknowledgmentList(BaseModel):
    items: list[ContractorAcknowledgmentResponse]
    count: int
