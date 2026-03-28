"""Schemas for geo.admin context overlay responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GeoLayerResult(BaseModel):
    """A single geo overlay layer result."""

    source: str
    label: str
    raw_attributes: dict[str, Any] = {}
    # Layer-specific parsed fields (optional, depend on layer type)
    zone: str | None = None
    value: str | None = None
    level_db: float | str | None = None
    suitability: str | None = None
    potential_kwh: float | str | None = None
    hazard_level: str | None = None
    zone_type: str | None = None
    status: str | None = None
    category: str | None = None
    name: str | None = None
    quality_class: str | None = None
    network_name: str | None = None


class GeoContextResponse(BaseModel):
    """Full geo context response for a building."""

    context: dict[str, Any] = {}
    fetched_at: str | None = None
    source_version: str | None = None
    cached: bool = False
    error: str | None = None
    detail: str | None = None


class GeoContextRefreshResponse(BaseModel):
    """Response after a forced refresh."""

    context: dict[str, Any] = {}
    fetched_at: datetime | None = None
    source_version: str = "geo.admin-v1"
    layers_count: int = 0
