"""Onboarding wizard schemas — EGID lookup + building creation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EgidLookupRequest(BaseModel):
    egid: int = Field(..., description="EGID number to look up in public sources")


class EgidLookupResult(BaseModel):
    found: bool
    egid: int
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    municipality_ofs: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    building_type: str | None = None
    floors_above: int | None = None
    surface_area_m2: float | None = None
    source_metadata: dict[str, Any] | None = None

    # Enrichment checklist
    has_address: bool = False
    has_coordinates: bool = False
    has_construction_year: bool = False
    has_building_type: bool = False
    has_floors: bool = False
    has_surface_area: bool = False


class OnboardingCreateRequest(BaseModel):
    egid: int
    address: str
    postal_code: str = Field(pattern=r"^\d{4}$")
    city: str
    canton: str = Field(min_length=2, max_length=2)
    municipality_ofs: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    building_type: str = "mixed"
    floors_above: int | None = None
    surface_area_m2: float | None = None
    source_metadata: dict[str, Any] | None = None
