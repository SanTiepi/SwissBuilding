"""BatiConnect — Pydantic schemas for DefectTimeline (DefectShield module)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DefectTimelineCreate(BaseModel):
    building_id: UUID
    diagnostic_id: UUID | None = None
    defect_type: Literal["construction", "pollutant", "structural", "installation", "other"]
    description: str | None = None
    discovery_date: date
    purchase_date: date | None = None


class DefectTimelineUpdate(BaseModel):
    status: Literal["active", "notified", "expired", "resolved"] | None = None
    description: str | None = None
    notified_at: datetime | None = None
    notification_pdf_url: str | None = None


class DefectTimelineResponse(BaseModel):
    id: UUID
    building_id: UUID
    diagnostic_id: UUID | None
    defect_type: str
    description: str | None
    discovery_date: date
    purchase_date: date | None
    notification_deadline: date
    guarantee_type: str
    prescription_date: date | None
    status: str
    notified_at: datetime | None
    notification_pdf_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DefectAlertResponse(BaseModel):
    building_id: UUID
    defect_id: UUID
    defect_type: str
    description: str | None
    notification_deadline: date
    days_remaining: int
    urgency: Literal["critical", "urgent", "warning", "normal"]

    model_config = ConfigDict(from_attributes=True)
