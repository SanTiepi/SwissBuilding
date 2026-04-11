"""Pydantic schemas for UnknownsLedger API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Read / response schemas
# ---------------------------------------------------------------------------


class UnknownEntryRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    case_id: uuid.UUID | None = None
    unknown_type: str
    subject: str
    description: str | None = None
    zone_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    severity: str
    blocks_safe_to_x: list[str] | None = None
    blocks_pack_types: list[str] | None = None
    risk_of_acting: str | None = None
    estimated_resolution_effort: str | None = None
    status: str
    resolved_at: datetime | None = None
    resolved_by_id: uuid.UUID | None = None
    resolution_method: str | None = None
    resolution_note: str | None = None
    detected_by: str
    source_type: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Resolve / accept-risk payloads
# ---------------------------------------------------------------------------


class ResolveUnknownRequest(BaseModel):
    method: str
    note: str | None = None


class AcceptRiskRequest(BaseModel):
    note: str  # required -- never silent


# ---------------------------------------------------------------------------
# Scan response
# ---------------------------------------------------------------------------


class ScanResultRead(BaseModel):
    total: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    blocking_safe_to_x: dict[str, int]
    created: int
    resolved: int


# ---------------------------------------------------------------------------
# Coverage map
# ---------------------------------------------------------------------------


class CoverageZone(BaseModel):
    zone_id: uuid.UUID
    zone_name: str
    status: str  # covered, gap, partial


class CoverageMapRead(BaseModel):
    covered: list[CoverageZone]
    gaps: list[CoverageZone]
    partial: list[CoverageZone]


# ---------------------------------------------------------------------------
# Impact summary
# ---------------------------------------------------------------------------


class UnknownsImpactRead(BaseModel):
    total_open: int
    critical_count: int
    blocked_safe_to_x: dict[str, int]
    blocked_pack_types: dict[str, int]
    most_urgent: list[UnknownEntryRead]
