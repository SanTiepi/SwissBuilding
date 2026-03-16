from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    body: str | None
    link: str | None
    status: str
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceRead(BaseModel):
    in_app_actions: bool
    in_app_invitations: bool
    in_app_exports: bool
    digest_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    in_app_actions: bool | None = None
    in_app_invitations: bool | None = None
    in_app_exports: bool | None = None
    digest_enabled: bool | None = None
