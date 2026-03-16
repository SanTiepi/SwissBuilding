"""
SwissBuildingOS - Extended Notification Preferences Schemas

Channel routing, quiet hours, and per-type granularity for notifications.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

NotificationChannel = Literal["in_app", "email", "digest"]


class NotificationTypePreference(BaseModel):
    type: str
    channels: list[NotificationChannel] = Field(default_factory=lambda: ["in_app"])
    enabled: bool = True


class QuietHours(BaseModel):
    enabled: bool = False
    start_hour: int = Field(default=22, ge=0, le=23)
    end_hour: int = Field(default=7, ge=0, le=23)
    timezone: str = "Europe/Zurich"


class FullNotificationPreferences(BaseModel):
    user_id: UUID
    type_preferences: list[NotificationTypePreference]
    quiet_hours: QuietHours
    digest_frequency: Literal["daily", "weekly", "never"] = "never"
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesUpdate(BaseModel):
    type_preferences: list[NotificationTypePreference] | None = None
    quiet_hours: QuietHours | None = None
    digest_frequency: Literal["daily", "weekly", "never"] | None = None
