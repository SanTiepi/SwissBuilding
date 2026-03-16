"""Pydantic v2 schemas for the Lab Result analysis service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------


class SampleResult(BaseModel):
    """Single sample with threshold comparison."""

    sample_id: UUID
    sample_number: str
    pollutant_type: str | None = None
    concentration: float | None = None
    unit: str | None = None
    threshold: float | None = None
    threshold_exceeded: bool = False
    ratio_to_threshold: float | None = None
    risk_level: str | None = None
    location_floor: str | None = None
    location_room: str | None = None
    diagnostic_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class PollutantStats(BaseModel):
    """Statistical summary for one pollutant type."""

    pollutant_type: str
    count: int = 0
    min_concentration: float | None = None
    max_concentration: float | None = None
    avg_concentration: float | None = None
    median_concentration: float | None = None
    unit: str | None = None
    threshold: float | None = None
    pass_count: int = 0
    fail_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class LabResultAnalysis(BaseModel):
    """Consolidated lab result analysis for a building."""

    building_id: UUID
    total_samples: int = 0
    samples_with_results: int = 0
    sample_results: list[SampleResult] = Field(default_factory=list)
    stats_by_pollutant: list[PollutantStats] = Field(default_factory=list)
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


class ResultAnomaly(BaseModel):
    """A single anomaly flag on a lab result."""

    anomaly_type: str  # at_threshold | extreme_outlier | conflicting_adjacent | age_inconsistent
    severity: str  # info | warning | critical
    sample_id: UUID
    sample_number: str
    description: str
    pollutant_type: str | None = None
    concentration: float | None = None

    model_config = ConfigDict(from_attributes=True)


class ResultAnomalyReport(BaseModel):
    """All anomalies detected for a building's lab results."""

    building_id: UUID
    anomalies: list[ResultAnomaly] = Field(default_factory=list)
    total: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    scanned_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------


class PollutantTrendPoint(BaseModel):
    """A single data point in a concentration trend."""

    date: str  # ISO date
    concentration: float
    sample_number: str
    sample_id: UUID

    model_config = ConfigDict(from_attributes=True)


class PollutantTrend(BaseModel):
    """Trend for one pollutant type."""

    pollutant_type: str
    unit: str | None = None
    data_points: list[PollutantTrendPoint] = Field(default_factory=list)
    trend_direction: str = "stable"  # increasing | stable | decreasing
    is_seasonal: bool = False

    model_config = ConfigDict(from_attributes=True)


class ResultTrends(BaseModel):
    """Temporal analysis of lab results for a building."""

    building_id: UUID
    trends: list[PollutantTrend] = Field(default_factory=list)
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------


class PollutantComplianceSummary(BaseModel):
    """Compliance summary for one pollutant."""

    pollutant_type: str
    total_samples: int = 0
    compliant: int = 0
    non_compliant: int = 0
    compliance_rate: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class LabSummaryReport(BaseModel):
    """Structured summary report of lab results for a building."""

    building_id: UUID
    total_samples: int = 0
    samples_with_results: int = 0
    samples_without_results: int = 0
    pollutant_summaries: list[PollutantComplianceSummary] = Field(default_factory=list)
    overall_compliance: bool = True
    anomaly_count: int = 0
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
