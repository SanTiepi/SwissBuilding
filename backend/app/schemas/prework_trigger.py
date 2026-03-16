"""Pydantic schemas for the persistent PreworkTrigger model."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

PreworkTriggerStatus = Literal["pending", "acknowledged", "resolved", "dismissed"]


class PreworkTriggerRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    trigger_type: str
    reason: str
    source_check: str
    legal_basis: str | None
    urgency: str
    escalation_level: float
    status: PreworkTriggerStatus
    acknowledged_by: uuid.UUID | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolved_reason: str | None
    assessment_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PreworkTriggerAcknowledge(BaseModel):
    """Payload to acknowledge a trigger (user has seen it)."""

    pass


class PreworkTriggerResolve(BaseModel):
    """Payload to resolve or dismiss a trigger."""

    status: Literal["resolved", "dismissed"] = "resolved"
    reason: str | None = None
