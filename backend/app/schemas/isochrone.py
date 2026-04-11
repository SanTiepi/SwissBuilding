"""Isochrone API response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IsochroneContour(BaseModel):
    """A single isochrone contour (GeoJSON polygon)."""

    minutes: int
    profile: str
    geometry: dict = Field(default_factory=dict, description="GeoJSON Polygon geometry")


class IsochroneResponse(BaseModel):
    """Response for isochrone endpoint."""

    building_id: str
    latitude: float
    longitude: float
    profile: str = "walking"
    contours: list[IsochroneContour] = []
    mobility_score: float | None = Field(None, ge=0, le=10, description="Mobility score 0-10")
    cached: bool = False
    error: str | None = None
