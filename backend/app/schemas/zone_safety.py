"""Schemas for zone safety status and occupant notices."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Zone Safety Status
# ---------------------------------------------------------------------------

VALID_SAFETY_LEVELS = {"safe", "restricted", "hazardous", "closed"}
VALID_RESTRICTION_TYPES = {"access_limited", "ppe_required", "evacuation", "no_access", None}
VALID_NOTICE_TYPES = {"safety_alert", "access_restriction", "work_schedule", "clearance"}
VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_AUDIENCES = {"all_occupants", "floor_occupants", "zone_occupants", "management_only"}


class ZoneSafetyStatusCreate(BaseModel):
    safety_level: str
    restriction_type: str | None = None
    hazard_types: list[str] | None = None
    assessment_notes: str | None = None
    valid_until: datetime | None = None


class ZoneSafetyStatusRead(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    building_id: uuid.UUID
    safety_level: str
    restriction_type: str | None
    hazard_types: list[str] | None
    assessed_by: uuid.UUID | None
    assessment_notes: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    is_current: bool
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Occupant Notice
# ---------------------------------------------------------------------------


class OccupantNoticeCreate(BaseModel):
    zone_id: uuid.UUID | None = None
    notice_type: str
    severity: str
    title: str
    body: str
    audience: str
    expires_at: datetime | None = None


class OccupantNoticeRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    zone_id: uuid.UUID | None
    notice_type: str
    severity: str
    title: str
    body: str
    audience: str
    status: str
    published_at: datetime | None
    expires_at: datetime | None
    created_by: uuid.UUID
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
