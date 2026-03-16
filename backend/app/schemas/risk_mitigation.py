"""Schemas for the Risk Mitigation Planner."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MitigationStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order: int
    pollutant_type: str
    intervention_type: str
    urgency_score: float
    estimated_cost_min_chf: float = 0.0
    estimated_cost_max_chf: float = 0.0
    dependencies: list[int] = Field(default_factory=list)
    rationale: str = ""
    work_category: str = "minor"
    regulatory_reference: str = ""


class MitigationPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    steps: list[MitigationStep] = Field(default_factory=list)
    total_cost_min_chf: float = 0.0
    total_cost_max_chf: float = 0.0
    total_duration_weeks: int = 0
    risk_reduction_percent: float = 0.0
    generated_at: datetime


class QuickWin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    action_description: str
    cost_estimate_chf: float = 0.0
    risk_reduction_score: float = 0.0
    work_category: str = "minor"


class DependencyEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    blocker: str
    blocked: str
    reason: str


class DependencyAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    dependencies: list[DependencyEdge] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    parallel_safe: list[str] = Field(default_factory=list)


class TimelineMilestone(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week: int
    description: str
    cost_chf: float = 0.0


class PlanTimeline(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    total_weeks: int = 0
    milestones: list[TimelineMilestone] = Field(default_factory=list)
    cumulative_cost_curve: list[float] = Field(default_factory=list)
