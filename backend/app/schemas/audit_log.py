"""Pydantic schemas for audit log entries."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: UUID | None
    details: dict | None
    ip_address: str | None
    timestamp: datetime

    # Flattened user info (populated by the API layer)
    user_email: str | None = None
    user_name: str | None = None
