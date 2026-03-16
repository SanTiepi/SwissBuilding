"""Pydantic v2 schemas for the Risk Aggregation service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# FN1: Unified Risk Score
# ---------------------------------------------------------------------------


class UnifiedRiskScore(BaseModel):
    """Composite risk score 0-100 with grade and peer comparison."""

    building_id: UUID
    overall_score: float  # 0-100
    grade: str  # A-F
    dimensions: dict[str, float]  # dimension -> weighted contribution
    peer_average: float  # average score across org buildings
    percentile: float  # 0-100, where the building stands vs peers
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN2: Risk Decomposition
# ---------------------------------------------------------------------------


class RiskContributor(BaseModel):
    """A single contributor to a risk dimension."""

    name: str
    impact: float  # contribution to dimension score
    description: str

    model_config = ConfigDict(from_attributes=True)


class RiskDimensionDetail(BaseModel):
    """Drill-down detail for a single risk dimension."""

    dimension: str
    raw_score: float  # 0-100
    weight: float
    weighted_score: float
    trend: str  # improving, stable, worsening
    top_contributors: list[RiskContributor]
    mitigation_options: list[str]

    model_config = ConfigDict(from_attributes=True)


class WaterfallSegment(BaseModel):
    """One segment of a waterfall chart."""

    dimension: str
    contribution: float  # positive contribution to total score
    cumulative: float

    model_config = ConfigDict(from_attributes=True)


class RiskDecomposition(BaseModel):
    """Full decomposition of a building's risk score."""

    building_id: UUID
    overall_score: float
    grade: str
    dimensions: list[RiskDimensionDetail]
    waterfall: list[WaterfallSegment]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN3: Risk Correlation Map
# ---------------------------------------------------------------------------


class RiskCorrelation(BaseModel):
    """Correlation between two risk dimensions."""

    source: str
    target: str
    strength: float  # 0.0 - 1.0
    direction: str  # positive, negative
    description: str

    model_config = ConfigDict(from_attributes=True)


class RiskCorrelationMap(BaseModel):
    """Map of correlations between risk dimensions for a building."""

    building_id: UUID
    correlations: list[RiskCorrelation]
    cascade_chains: list[list[str]]  # ordered chains of risk propagation
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN4: Portfolio Risk Matrix
# ---------------------------------------------------------------------------


class BuildingRiskCell(BaseModel):
    """One cell in the portfolio risk matrix (building x dimension)."""

    building_id: UUID
    address: str
    city: str
    dimension: str
    score: float  # 0-100

    model_config = ConfigDict(from_attributes=True)


class RiskHotspot(BaseModel):
    """A systemic risk hotspot identified across the portfolio."""

    dimension: str
    affected_building_count: int
    average_score: float
    severity: str  # low, medium, high, critical

    model_config = ConfigDict(from_attributes=True)


class PortfolioRiskMatrix(BaseModel):
    """2D matrix of buildings x risk dimensions with hotspots."""

    organization_id: UUID
    building_count: int
    dimensions: list[str]
    cells: list[BuildingRiskCell]
    hotspots: list[RiskHotspot]
    systemic_patterns: list[str]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
