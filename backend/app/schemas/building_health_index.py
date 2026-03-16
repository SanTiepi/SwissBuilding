"""Pydantic v2 schemas for the Building Health Index."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DimensionScore(BaseModel):
    """Score for a single health dimension."""

    dimension: str
    score: float  # 0-100
    weight: float
    weighted_score: float
    contributing_factors: list[str]

    model_config = ConfigDict(from_attributes=True)


class HealthIndex(BaseModel):
    """Composite building health index result."""

    building_id: UUID
    overall_score: float  # 0-100
    grade: str  # A-F
    trend: str  # improving, stable, declining
    dimensions: list[DimensionScore]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImprovementLever(BaseModel):
    """A recommended action to improve health score."""

    dimension: str
    description: str
    potential_gain: float  # points
    effort: str  # low, medium, high
    priority: int  # 1 = highest

    model_config = ConfigDict(from_attributes=True)


class HealthBreakdown(BaseModel):
    """Detailed per-dimension breakdown with worst contributors and levers."""

    building_id: UUID
    overall_score: float
    grade: str
    dimensions: list[DimensionScore]
    worst_contributors: list[str]
    improvement_levers: list[ImprovementLever]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrajectoryPoint(BaseModel):
    """A single point on a health trajectory curve."""

    month: int  # 1-12
    score: float

    model_config = ConfigDict(from_attributes=True)


class RecommendedAction(BaseModel):
    """Action recommended to reach a target score."""

    description: str
    expected_gain: float
    dimension: str

    model_config = ConfigDict(from_attributes=True)


class HealthTrajectory(BaseModel):
    """12-month health trajectory projection."""

    building_id: UUID
    current_score: float
    decay_curve: list[TrajectoryPoint]
    improvement_curve: list[TrajectoryPoint]
    recommended_actions: list[RecommendedAction]
    projected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingHealthSummary(BaseModel):
    """Summary of a single building's health for portfolio view."""

    building_id: UUID
    address: str
    city: str
    score: float
    grade: str
    trend: str

    model_config = ConfigDict(from_attributes=True)


class PortfolioHealthDashboard(BaseModel):
    """Org-level portfolio health dashboard."""

    organization_id: UUID
    building_count: int
    average_score: float
    average_grade: str
    health_distribution: dict[str, int]  # grade -> count
    trend: str  # improving, stable, declining
    best_buildings: list[BuildingHealthSummary]
    worst_buildings: list[BuildingHealthSummary]
    threshold_crossings: list[BuildingHealthSummary]  # dropping below 50
    aggregate_improvement_cost_chf: float
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
