"""
SwissBuildingOS - Campaign Tracking Schemas

Per-building execution tracking within campaigns.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BuildingCampaignStatus(BaseModel):
    """Status of a single building within a campaign."""

    building_id: UUID
    status: str = "not_started"  # not_started | in_progress | blocked | completed | skipped
    started_at: datetime | None = None
    completed_at: datetime | None = None
    blocker_reason: str | None = None
    notes: str | None = None
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)

    model_config = ConfigDict(from_attributes=True)


class BuildingStatusUpdate(BaseModel):
    """Payload to update a building's tracking status."""

    status: str  # not_started | in_progress | blocked | completed | skipped
    blocker_reason: str | None = None
    notes: str | None = None
    progress_pct: float | None = Field(default=None, ge=0.0, le=100.0)


class CampaignProgress(BaseModel):
    """Aggregated progress metrics for a campaign."""

    campaign_id: UUID
    total_buildings: int
    by_status: dict[str, int]
    overall_progress_pct: float
    estimated_completion: datetime | None = None
    velocity_per_day: float | None = None
    at_risk_count: int = 0


class CampaignExecutionSummary(BaseModel):
    """Full execution summary with stale detection."""

    campaign_id: UUID
    campaign_name: str
    progress: CampaignProgress
    recent_updates: list[dict]
    stale_buildings: list[UUID]


class BatchStatusUpdate(BaseModel):
    """Payload for batch status updates."""

    building_ids: list[UUID]
    status: str
