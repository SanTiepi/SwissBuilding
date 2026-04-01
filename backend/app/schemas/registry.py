"""Schemas for Swiss public registry lookups and building enrichment."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RegistryLookupResult(BaseModel):
    """Result of a RegBL EGID lookup."""

    egid: int
    source: str = "regbl"
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    construction_year: int | None = None
    building_category: str | None = None
    building_class: str | None = None
    floors: int | None = None
    area: float | None = None
    heating_type: str | None = None
    energy_source: str | None = None
    renovation_year: int | None = None
    coordinates: dict[str, float] | None = None
    raw_attributes: dict[str, Any] = {}


class AddressSearchResult(BaseModel):
    """Single result from a Swisstopo address search."""

    source: str = "swisstopo"
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    lat: float | None = None
    lng: float | None = None
    egid: int | None = None
    feature_id: str | None = None


class HazardLevel(BaseModel):
    """A single hazard risk level."""

    level: str = "unknown"
    description: str | None = None
    source: str | None = None


class NaturalHazardsResult(BaseModel):
    """Natural hazards at a geographic point."""

    flood_risk: HazardLevel | None = None
    landslide_risk: HazardLevel | None = None
    avalanche_risk: HazardLevel | None = None
    earthquake_risk: HazardLevel | None = None


class EnrichmentResult(BaseModel):
    """Result of auto-enriching a building from public registries."""

    building_id: str
    updated_fields: dict[str, Any] = {}
    source: str = "regbl+geo.admin"
    egid_found: bool = False
    hazards_fetched: bool = False
