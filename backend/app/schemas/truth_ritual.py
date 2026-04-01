import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

VALID_RITUAL_TYPES = {"validate", "freeze", "publish", "transfer", "acknowledge", "reopen", "supersede", "receipt"}
VALID_TARGET_TYPES = {
    "evidence",
    "claim",
    "decision",
    "publication",
    "document",
    "extraction",
    "pack",
    "passport",
    "case",
}


class TruthRitualBase(BaseModel):
    target_type: str
    target_id: uuid.UUID
    reason: str | None = None
    case_id: uuid.UUID | None = None


class TruthRitualValidate(TruthRitualBase):
    pass


class TruthRitualFreeze(TruthRitualBase):
    pass


class TruthRitualPublish(TruthRitualBase):
    recipient_type: str | None = None
    recipient_id: uuid.UUID | None = None
    delivery_method: str | None = None


class TruthRitualTransfer(TruthRitualBase):
    recipient_type: str
    recipient_id: uuid.UUID
    delivery_method: str


class TruthRitualAcknowledge(TruthRitualBase):
    receipt_hash: str | None = None


class TruthRitualReopen(TruthRitualBase):
    reason: str  # required for reopen


class TruthRitualSupersede(TruthRitualBase):
    new_target_id: uuid.UUID


class TruthRitualReceipt(TruthRitualBase):
    recipient_id: uuid.UUID
    receipt_hash: str
    delivery_method: str


class TruthRitualResponse(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    ritual_type: str
    performed_by_id: uuid.UUID
    organization_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    reason: str | None
    case_id: uuid.UUID | None
    content_hash: str | None
    version: int | None
    recipient_type: str | None
    recipient_id: uuid.UUID | None
    delivery_method: str | None
    acknowledged_by_id: uuid.UUID | None
    receipt_hash: str | None
    supersedes_id: uuid.UUID | None
    reopen_reason: str | None
    performed_at: datetime | None
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TruthRitualList(BaseModel):
    items: list[TruthRitualResponse]
    count: int
