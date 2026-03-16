"""Schemas for counterfactual / what-if analysis and stress testing."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Scenario & Impact
# ---------------------------------------------------------------------------


class CounterfactualScenario(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    scenario_type: str  # delayed_action | early_intervention | regulation_change | budget_cut | natural_event
    description: str = ""
    parameters: dict[str, str] = Field(default_factory=dict)


class ImpactMetric(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_name: str
    baseline_value: float = 0.0
    counterfactual_value: float = 0.0
    delta: float = 0.0
    delta_pct: float = 0.0
    unit: str = ""
    direction: str = "neutral"  # better | worse | neutral


class CounterfactualResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    scenario: CounterfactualScenario
    impacts: list[ImpactMetric] = Field(default_factory=list)
    overall_impact: str = "neutral"  # positive | negative | neutral
    risk_level_change: str | None = None
    cost_impact_chf: float = 0.0
    generated_at: datetime


# ---------------------------------------------------------------------------
# Stress Test
# ---------------------------------------------------------------------------


class StressTestParameter(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter_name: str
    baseline: float = 0.0
    stressed: float = 0.0
    unit: str = ""


class StressTestResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    stress_type: str  # regulatory_tightening | cost_increase | timeline_acceleration | resource_scarcity
    parameters: list[StressTestParameter] = Field(default_factory=list)
    buildings_failing: int = 0
    new_violations: int = 0
    additional_cost: float = 0.0
    resilience_score: float = 0.0  # 0.0-1.0
    generated_at: datetime


# ---------------------------------------------------------------------------
# Timeline Alternatives
# ---------------------------------------------------------------------------


class TimelineAlternative(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alternative_id: str
    description: str = ""
    start_date: date
    completion_date: date
    total_cost: float = 0.0
    risk_reduction_pct: float = 0.0
    is_optimal: bool = False


class BuildingTimelineAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    current_timeline_cost: float = 0.0
    alternatives: list[TimelineAlternative] = Field(default_factory=list)
    optimal_savings: float = 0.0
    generated_at: datetime


# ---------------------------------------------------------------------------
# Portfolio Stress Test
# ---------------------------------------------------------------------------


class PortfolioStressTest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    stress_type: str
    total_buildings_tested: int = 0
    buildings_resilient: int = 0
    buildings_at_risk: int = 0
    average_resilience_score: float = 0.0
    total_additional_cost: float = 0.0
    generated_at: datetime
