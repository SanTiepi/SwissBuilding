"""Pydantic v2 schemas for the Spatial Risk Mapping service."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ColorTier(StrEnum):
    green = "green"
    yellow = "yellow"
    orange = "orange"
    red = "red"


class AreaStatus(StrEnum):
    safe = "safe"
    restricted = "restricted"
    unknown = "unknown"


class GapPriority(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


# --- FN1: Building Risk Map ---


class ZoneRiskOverlay(BaseModel):
    """Risk overlay for a single zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    composite_risk_score: float = Field(ge=0.0, le=1.0)
    color_tier: ColorTier
    dominant_pollutant: str | None = None
    sample_density: int = 0
    pollutant_types: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class BuildingRiskMap(BaseModel):
    """Zone-by-zone risk overlay for a building."""

    building_id: UUID
    zones: list[ZoneRiskOverlay]
    total_zones: int = 0
    zones_at_risk: int = 0
    overall_risk_score: float = Field(ge=0.0, le=1.0)
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN2: Floor Risk Profile ---


class FloorZoneDetail(BaseModel):
    """Zone detail within a floor risk profile."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    area_status: AreaStatus
    risk_score: float = Field(ge=0.0, le=1.0)
    color_tier: ColorTier
    pollutants: list[str] = []
    sample_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PollutantDistribution(BaseModel):
    """Distribution of a pollutant type on a floor."""

    pollutant_type: str
    zone_count: int = 0
    sample_count: int = 0
    max_concentration: float | None = None
    unit: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FloorRiskProfile(BaseModel):
    """Risk profile for a single floor."""

    building_id: UUID
    floor_number: int
    zones: list[FloorZoneDetail]
    pollutant_distribution: list[PollutantDistribution]
    safe_zones: int = 0
    restricted_zones: int = 0
    unknown_zones: int = 0
    coverage_percentage: float = Field(ge=0.0, le=100.0)
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN3: Risk Propagation Analysis ---


class PropagationEdge(BaseModel):
    """Contamination risk propagation between adjacent zones."""

    source_zone_id: UUID
    source_zone_name: str
    target_zone_id: UUID
    target_zone_name: str
    source_risk_score: float = Field(ge=0.0, le=1.0)
    propagated_risk_score: float = Field(ge=0.0, le=1.0)
    dominant_pollutant: str | None = None
    relationship: str = "parent_child"

    model_config = ConfigDict(from_attributes=True)


class ZonePropagatedRisk(BaseModel):
    """A zone with its own risk and propagated risk from neighbors."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    own_risk_score: float = Field(ge=0.0, le=1.0)
    propagated_risk_score: float = Field(ge=0.0, le=1.0)
    combined_risk_score: float = Field(ge=0.0, le=1.0)
    color_tier: ColorTier
    contributing_zones: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class RiskPropagationAnalysis(BaseModel):
    """Adjacent zone contamination risk analysis."""

    building_id: UUID
    zones: list[ZonePropagatedRisk]
    edges: list[PropagationEdge]
    total_zones: int = 0
    zones_with_elevated_risk: int = 0
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN4: Spatial Coverage Gaps ---


class CoverageGap(BaseModel):
    """A zone or area that needs investigation."""

    zone_id: UUID | None = None
    zone_name: str | None = None
    zone_type: str | None = None
    floor_number: int | None = None
    gap_type: str
    priority: GapPriority
    reason: str

    model_config = ConfigDict(from_attributes=True)


class FloorCoverageStatus(BaseModel):
    """Coverage status for a single floor."""

    floor_number: int
    total_zones: int = 0
    sampled_zones: int = 0
    has_diagnostic: bool = False
    coverage_percentage: float = Field(ge=0.0, le=100.0)

    model_config = ConfigDict(from_attributes=True)


class SpatialCoverageGaps(BaseModel):
    """Zones without samples, floors without diagnostics, areas needing investigation."""

    building_id: UUID
    gaps: list[CoverageGap]
    floor_coverage: list[FloorCoverageStatus]
    total_zones: int = 0
    sampled_zones: int = 0
    unsampled_zones: int = 0
    overall_coverage_percentage: float = Field(ge=0.0, le=100.0)
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
