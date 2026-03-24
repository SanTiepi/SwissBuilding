"""BatiConnect — Intake Request schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IntakeRequestCreate(BaseModel):
    """Public submission — no auth required."""

    requester_name: str
    requester_email: str
    requester_phone: str | None = None
    requester_company: str | None = None
    building_address: str
    building_egid: str | None = None
    building_city: str | None = None
    building_postal_code: str | None = None
    request_type: str  # asbestos_diagnostic|pcb_diagnostic|lead_diagnostic|multi_pollutant|consultation|other
    description: str | None = None
    urgency: str = "standard"  # standard|urgent|emergency
    attachments: list[dict] | None = None
    source: str = "website"  # website|email|phone|referral|other


class IntakeRequestRead(BaseModel):
    id: UUID
    status: str
    requester_name: str
    requester_email: str
    requester_phone: str | None
    requester_company: str | None
    building_address: str
    building_egid: str | None
    building_city: str | None
    building_postal_code: str | None
    request_type: str
    description: str | None
    urgency: str
    attachments: list[dict] | None
    converted_contact_id: UUID | None
    converted_building_id: UUID | None
    converted_mission_order_id: UUID | None
    qualified_by_user_id: UUID | None
    qualified_at: datetime | None
    notes: str | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntakeQualifyRequest(BaseModel):
    notes: str | None = None


class IntakeConvertRequest(BaseModel):
    organization_id: UUID | None = None
    notes: str | None = None


class IntakeRejectRequest(BaseModel):
    reason: str | None = None
