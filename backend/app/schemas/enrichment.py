"""Schemas for building auto-enrichment pipeline."""

from __future__ import annotations

import uuid as _uuid

from pydantic import BaseModel, Field


class EnrichmentRequest(BaseModel):
    """Request body for single-building enrichment."""

    building_id: _uuid.UUID
    skip_geocode: bool = False
    skip_regbl: bool = False
    skip_ai: bool = False
    skip_cadastre: bool = False
    skip_image: bool = False


class EnrichmentResult(BaseModel):
    """Result of enriching one building."""

    building_id: _uuid.UUID
    geocoded: bool = False
    regbl_found: bool = False
    egrid_found: bool = False
    image_url: str | None = None
    ai_enriched: bool = False
    # New enrichment sources
    radon_fetched: bool = False
    natural_hazards_fetched: bool = False
    noise_fetched: bool = False
    solar_fetched: bool = False
    heritage_fetched: bool = False
    transport_fetched: bool = False
    seismic_fetched: bool = False
    water_protection_fetched: bool = False
    neighborhood_score: float | None = None
    pollutant_risk_computed: bool = False
    accessibility_computed: bool = False
    subsidies_computed: bool = False
    fields_updated: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BatchEnrichmentRequest(BaseModel):
    """Request body for batch enrichment."""

    org_id: _uuid.UUID | None = None
    skip_geocode: bool = False
    skip_regbl: bool = False
    skip_ai: bool = False


class BatchEnrichmentResult(BaseModel):
    """Result of batch enrichment."""

    total: int = 0
    enriched: int = 0
    error_count: int = 0
    results: list[EnrichmentResult] = Field(default_factory=list)


class EnrichmentStatus(BaseModel):
    """Current enrichment status of a building."""

    building_id: _uuid.UUID
    has_coordinates: bool = False
    has_egid: bool = False
    has_egrid: bool = False
    has_construction_year: bool = False
    has_floors: bool = False
    has_image_url: bool = False
    has_ai_description: bool = False
    enrichment_metadata: dict | None = None
