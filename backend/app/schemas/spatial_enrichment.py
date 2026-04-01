"""Schemas for swissBUILDINGS3D spatial enrichment responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SpatialEnrichmentResponse(BaseModel):
    """Spatial enrichment data for a building."""

    footprint_wkt: str | None = None
    height_m: float | None = None
    roof_type: str | None = None
    volume_m3: float | None = None
    surface_m2: float | None = None
    floors: int | None = None
    source: str | None = None
    source_version: str | None = None
    fetched_at: str | None = None
    cached: bool = False
    error: str | None = None
    detail: str | None = None
    raw_attributes: dict[str, Any] = {}


class SpatialEnrichmentRefreshResponse(BaseModel):
    """Response after a forced spatial refresh."""

    footprint_wkt: str | None = None
    height_m: float | None = None
    roof_type: str | None = None
    volume_m3: float | None = None
    surface_m2: float | None = None
    floors: int | None = None
    source: str | None = None
    source_version: str | None = None
    fetched_at: datetime | None = None
    raw_attributes: dict[str, Any] = {}
    building_updated: bool = False
