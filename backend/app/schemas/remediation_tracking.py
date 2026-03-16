"""Schemas for Remediation Tracking."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RemediationPollutantStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    status: str  # not_needed / pending / in_progress / completed / verified
    affected_zones: int = 0
    remediated_zones: int = 0
    progress_percentage: float = 0.0
    blocking_issues: list[str] = Field(default_factory=list)


class BuildingRemediationStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    pollutants: list[RemediationPollutantStatus] = Field(default_factory=list)
    overall_progress_percentage: float = 0.0


class PollutantTimeline(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    estimated_start: date | None = None
    estimated_completion: date | None = None
    duration_days: int = 0
    dependencies: list[str] = Field(default_factory=list)
    parallel_possible: bool = False


class BuildingRemediationTimeline(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    timelines: list[PollutantTimeline] = Field(default_factory=list)


class CostPhaseBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phase: str
    estimated_cost: float = 0.0
    actual_cost: float = 0.0


class PollutantCostTracker(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    variance_percentage: float = 0.0
    budget_status: str = "on_track"  # under / on_track / over
    breakdown_by_phase: list[CostPhaseBreakdown] = Field(default_factory=list)


class BuildingCostTracker(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    costs: list[PollutantCostTracker] = Field(default_factory=list)
    total_estimated: float = 0.0
    total_actual: float = 0.0


class BuildingAtRiskOfDelay(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    overdue_actions: int = 0
    blocking_pollutants: list[str] = Field(default_factory=list)


class PollutantDistribution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    building_count: int = 0
    avg_progress: float = 0.0


class PortfolioRemediationDashboard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings_needing_remediation: int = 0
    by_pollutant_type: list[PollutantDistribution] = Field(default_factory=list)
    overall_progress_pct: float = 0.0
    estimated_total_cost: float = 0.0
    buildings_at_risk_of_delay: list[BuildingAtRiskOfDelay] = Field(default_factory=list)
