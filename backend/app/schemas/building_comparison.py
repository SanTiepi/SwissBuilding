"""Pydantic v2 schemas for Building Comparison."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BuildingComparisonRequest(BaseModel):
    """Request body for comparing buildings."""

    building_ids: list[str] = Field(..., min_length=2, max_length=10)

    model_config = ConfigDict(from_attributes=True)


class BuildingComparisonEntry(BaseModel):
    """Comparison data for a single building."""

    building_id: str
    building_name: str
    address: str
    passport_grade: str | None = None
    passport_score: float | None = None
    trust_score: float | None = None
    completeness_score: float | None = None
    readiness_summary: dict[str, bool] = Field(default_factory=dict)
    open_actions_count: int = 0
    open_unknowns_count: int = 0
    contradictions_count: int = 0
    diagnostic_count: int = 0
    last_diagnostic_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BuildingComparison(BaseModel):
    """Aggregated comparison result for multiple buildings."""

    buildings: list[BuildingComparisonEntry]
    comparison_dimensions: list[str]
    best_passport: str | None = None
    worst_passport: str | None = None
    average_trust: float = 0.0
    average_completeness: float = 0.0

    model_config = ConfigDict(from_attributes=True)
