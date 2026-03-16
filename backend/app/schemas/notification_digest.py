"""
SwissBuildingOS - Notification Digest Schemas

Structured digest summaries aggregating notifications, actions,
deadlines, and signals for daily/weekly delivery.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DigestSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    items: list[dict]
    count: int


class DigestMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_notifications: int
    unread_count: int
    actions_due_soon: int
    overdue_actions: int
    new_signals: int
    upcoming_deadlines: int


class NotificationDigest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    period: str  # daily | weekly
    period_start: datetime
    period_end: datetime
    metrics: DigestMetrics
    sections: list[DigestSection]
    generated_at: datetime


class DigestPreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    period: str
    headline: str
    has_urgent: bool
    total_items: int
