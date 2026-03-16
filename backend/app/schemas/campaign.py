from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    title: str
    campaign_type: str
    description: str | None = None
    priority: str = "medium"
    organization_id: UUID | None = None
    building_ids: list[UUID] | None = None
    date_start: date | None = None
    date_end: date | None = None
    budget_chf: float | None = None
    criteria_json: dict[str, Any] | None = None
    notes: str | None = None


class CampaignUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    campaign_type: str | None = None
    status: str | None = None
    priority: str | None = None
    organization_id: UUID | None = None
    building_ids: list[UUID] | None = None
    date_start: date | None = None
    date_end: date | None = None
    budget_chf: float | None = None
    spent_chf: float | None = None
    criteria_json: dict[str, Any] | None = None
    notes: str | None = None


class CampaignResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    campaign_type: str
    status: str
    priority: str
    organization_id: UUID | None
    building_ids: list[UUID] | None
    target_count: int
    completed_count: int
    progress_pct: float
    date_start: date | None
    date_end: date | None
    budget_chf: float | None
    spent_chf: float | None
    criteria_json: dict[str, Any] | None
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignImpact(BaseModel):
    buildings_affected: int
    actions_total: int
    actions_completed: int
    actions_in_progress: int
    completion_rate: float
    velocity: float
    budget_utilization: float
    estimated_completion_date: date | None
    days_remaining: int | None
    is_at_risk: bool


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int
    page: int
    size: int
    pages: int
