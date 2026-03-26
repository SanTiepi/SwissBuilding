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
    # Extended enrichment sources
    railway_noise_fetched: bool = False
    aircraft_noise_fetched: bool = False
    building_zones_fetched: bool = False
    contaminated_sites_fetched: bool = False
    groundwater_zones_fetched: bool = False
    flood_zones_fetched: bool = False
    mobile_coverage_fetched: bool = False
    broadband_fetched: bool = False
    ev_charging_fetched: bool = False
    thermal_networks_fetched: bool = False
    protected_monuments_fetched: bool = False
    agricultural_zones_fetched: bool = False
    forest_reserves_fetched: bool = False
    military_zones_fetched: bool = False
    accident_sites_fetched: bool = False
    osm_amenities_fetched: bool = False
    osm_building_fetched: bool = False
    climate_computed: bool = False
    nearest_stops_fetched: bool = False
    # Computed scores
    connectivity_score: float | None = None
    environmental_risk_score: float | None = None
    livability_score: float | None = None
    renovation_potential_computed: bool = False
    overall_intelligence_computed: bool = False
    overall_intelligence_score: int | None = None
    overall_intelligence_grade: str | None = None
    # Enrichment layer 2: lifecycle, planning, compliance, financial, narrative
    component_lifecycle_computed: bool = False
    renovation_plan_computed: bool = False
    regulatory_compliance_computed: bool = False
    financial_impact_computed: bool = False
    building_narrative_computed: bool = False
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
