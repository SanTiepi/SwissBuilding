"""FreshnessWatch — Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReactionItem(BaseModel):
    """Single reaction to be executed in response to an external change."""

    type: str  # template_invalidation | safe_to_x_refresh | pack_invalidation | blocker_refresh | notification
    target: str | None = None
    scope: str | None = None


class FreshnessWatchCreate(BaseModel):
    delta_type: str
    title: str
    description: str | None = None
    canton: str | None = None
    jurisdiction_id: UUID | None = None
    affected_work_families: list[str] | None = None
    affected_procedure_types: list[str] | None = None
    severity: str = "info"
    reactions: list[ReactionItem] | None = None
    source_registry_id: UUID | None = None
    source_url: str | None = None
    effective_date: date | None = None


class FreshnessWatchRead(BaseModel):
    id: UUID
    source_registry_id: UUID | None
    delta_type: str
    title: str
    description: str | None
    canton: str | None
    jurisdiction_id: UUID | None
    affected_work_families: list[str] | None
    affected_procedure_types: list[str] | None
    severity: str
    affected_buildings_estimate: int | None
    reactions: list[dict] | None
    status: str
    reviewed_by_id: UUID | None
    reviewed_at: datetime | None
    applied_at: datetime | None
    dismiss_reason: str | None
    source_url: str | None
    detected_at: datetime | None
    effective_date: date | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class FreshnessWatchDismiss(BaseModel):
    reason: str


class FreshnessWatchDashboard(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_delta_type: dict[str, int]
    by_canton: dict[str, int]
    by_status: dict[str, int]
    critical_pending: int


class FreshnessWatchImpact(BaseModel):
    entry_id: UUID
    affected_buildings_estimate: int
    affected_procedures: list[str]
    affected_packs: list[str]
    reactions_summary: list[dict]
