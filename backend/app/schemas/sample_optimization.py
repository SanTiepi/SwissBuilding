"""Pydantic v2 schemas for sample optimization service."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- FN1: optimize_sampling_plan ---


class RecommendedSample(BaseModel):
    """A single recommended sample location."""

    zone_id: UUID | None = None
    zone_name: str
    zone_type: str
    pollutant_type: str
    sample_method: str  # bulk, air, wipe, radon_detector
    priority: str  # critical, high, medium, low
    reason: str  # unsampled, outdated, high_risk, coverage_gap
    estimated_cost_chf: float

    model_config = ConfigDict(from_attributes=True)


class SamplingOptimizationResult(BaseModel):
    """Optimized sampling plan for a building."""

    building_id: UUID
    total_zones: int
    zones_sampled: int
    zones_needing_samples: int
    recommended_samples: list[RecommendedSample]
    total_estimated_cost_chf: float
    coverage_before: float
    coverage_after: float

    model_config = ConfigDict(from_attributes=True)


# --- FN2: estimate_sampling_cost ---


class PollutantCostBreakdown(BaseModel):
    """Cost breakdown for a single pollutant type."""

    pollutant_type: str
    sample_count: int
    cost_per_sample_chf: float
    total_chf: float

    model_config = ConfigDict(from_attributes=True)


class SamplingCostEstimate(BaseModel):
    """Full cost estimate for recommended sampling."""

    building_id: UUID
    pollutant_breakdown: list[PollutantCostBreakdown]
    total_samples: int
    total_cost_chf: float
    lab_turnaround_days: int

    model_config = ConfigDict(from_attributes=True)


# --- FN3: evaluate_sampling_adequacy ---


class ZoneTypeCoverage(BaseModel):
    """Sampling coverage for a zone type."""

    zone_type: str
    total_zones: int
    sampled_zones: int
    coverage_pct: float

    model_config = ConfigDict(from_attributes=True)


class PollutantAdequacy(BaseModel):
    """Adequacy info for a single pollutant."""

    pollutant_type: str
    samples_count: int
    min_recommended: int
    is_adequate: bool

    model_config = ConfigDict(from_attributes=True)


class SamplingAdequacyResult(BaseModel):
    """Is current sampling sufficient?"""

    building_id: UUID
    is_adequate: bool
    confidence_level: float  # 0.0 - 1.0
    overall_coverage_pct: float
    zone_type_coverage: list[ZoneTypeCoverage]
    pollutant_adequacy: list[PollutantAdequacy]
    recommended_additional_samples: int

    model_config = ConfigDict(from_attributes=True)


# --- FN4: get_portfolio_sampling_status ---


class BuildingSamplingStatus(BaseModel):
    """Sampling status for a single building in a portfolio."""

    building_id: UUID
    address: str
    is_adequate: bool
    coverage_pct: float
    needs_resampling: bool
    estimated_cost_chf: float
    priority: str  # critical, high, medium, low

    model_config = ConfigDict(from_attributes=True)


class PortfolioSamplingStatus(BaseModel):
    """Org-level sampling status."""

    organization_id: UUID
    total_buildings: int
    buildings_adequate: int
    buildings_needing_resampling: int
    total_estimated_cost_chf: float
    priority_queue: list[BuildingSamplingStatus]

    model_config = ConfigDict(from_attributes=True)
