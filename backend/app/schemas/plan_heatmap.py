"""Pydantic schemas for Plan Heatmap (proof overlay)."""

from pydantic import BaseModel, ConfigDict


class HeatmapPoint(BaseModel):
    """A single point on the plan heatmap."""

    x: float  # 0.0-1.0 relative
    y: float  # 0.0-1.0 relative
    intensity: float  # 0.0-1.0
    category: str  # "trust", "unknown", "contradiction", "hazard", "sample"
    label: str | None = None
    annotation_id: str | None = None
    zone_id: str | None = None
    decay_factor: float = 1.0  # 1.0 = no decay, 0.5 = >2y old, 0.25 = >5y old
    confidence: float | None = None  # sample-linked confidence (0.0-1.0)

    model_config = ConfigDict(from_attributes=True)


class PlanHeatmap(BaseModel):
    """Aggregated heatmap data for a technical plan."""

    plan_id: str
    building_id: str
    total_points: int
    coverage_score: float  # 0.0-1.0, how well the plan is documented
    points: list[HeatmapPoint]
    summary: dict[str, int]  # counts by category

    model_config = ConfigDict(from_attributes=True)


class ZoneHeatmapStats(BaseModel):
    """Aggregated heatmap statistics for a single zone."""

    zone_id: str
    zone_name: str
    point_count: int
    avg_intensity: float
    coverage_score: float  # 0.0-1.0

    model_config = ConfigDict(from_attributes=True)


class CoverageGap(BaseModel):
    """A detected coverage gap in a plan."""

    zone_id: str
    zone_name: str
    gap_type: str  # "no_annotations", "low_density", "stale_data"
    description: str

    model_config = ConfigDict(from_attributes=True)


class CoverageGapReport(BaseModel):
    """Full coverage gap report for a plan."""

    plan_id: str
    building_id: str
    gaps: list[CoverageGap]
    overall_coverage: float  # 0.0-1.0

    model_config = ConfigDict(from_attributes=True)
