from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InvitationCreate(BaseModel):
    email: str
    role: str
    organization_id: UUID | None = None


class InvitationRead(BaseModel):
    id: UUID
    email: str
    role: str
    organization_id: UUID | None
    status: str
    token: str
    invited_by: UUID
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    token: str
    password: str
    first_name: str
    last_name: str
    language: str = "fr"
