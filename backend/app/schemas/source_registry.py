"""Schemas for source registry and source health."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SourceRegistryRead(BaseModel):
    """Read schema for a source registry entry."""

    id: UUID
    name: str
    display_name: str
    description: str | None = None
    family: str
    circle: int
    source_class: str
    access_mode: str
    base_url: str | None = None
    freshness_policy: str = "on_demand"
    cache_ttl_hours: int | None = None
    trust_posture: str
    geographic_scope: str = "switzerland"
    canton_scope: list[str] | None = None
    workspace_consumers: list[str] | None = None
    status: str = "active"
    license_notes: str | None = None
    fallback_source_name: str | None = None
    priority: str = "now"
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SourceHealthEventRead(BaseModel):
    """Read schema for a source health event."""

    id: UUID
    source_id: UUID
    event_type: str
    description: str | None = None
    error_detail: str | None = None
    affected_buildings_count: int | None = None
    fallback_used: bool = False
    fallback_source_name: str | None = None
    detected_at: datetime | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class SourceHealthSummary(BaseModel):
    """Health summary for a single source."""

    source_name: str
    display_name: str
    status: str
    last_event_type: str | None = None
    last_event_at: datetime | None = None
    events_24h: int = 0
    errors_24h: int = 0


class SourceHealthDashboard(BaseModel):
    """Health overview across all active sources."""

    total_sources: int = 0
    active: int = 0
    degraded: int = 0
    unavailable: int = 0
    sources: list[SourceHealthSummary] = []


class SourceFreshnessCheck(BaseModel):
    """Result of a source freshness check."""

    source_name: str
    is_fresh: bool
    cache_ttl_hours: int | None = None
    last_fetched_at: datetime | None = None
    age_hours: float | None = None
