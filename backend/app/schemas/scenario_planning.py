"""Pydantic schemas for scenario planning (what-if analysis)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class InterventionConfig(BaseModel):
    """Single intervention within a scenario."""

    intervention_type: str
    pollutant: str
    estimated_cost_chf: float = 0.0
    duration_months: float = 1.0
    surface_m2: float | None = None
    description: str | None = None


class ScenarioCreateRequest(BaseModel):
    """Request body for creating / evaluating a single scenario."""

    building_id: uuid.UUID
    name: str = "Scenario"
    interventions: list[InterventionConfig] = Field(default_factory=list, max_length=20)


class CompareRequest(BaseModel):
    """Request body for side-by-side scenario comparison."""

    building_id: uuid.UUID
    scenarios: list[ScenarioCreateRequest] = Field(min_length=1, max_length=5)


class OptimalRequest(BaseModel):
    """Request body for auto-optimal scenario generation."""

    building_id: uuid.UUID
    budget_limit_chf: float
    time_limit_months: float


class SensitivityRequest(BaseModel):
    """Request body for sensitivity analysis."""

    building_id: uuid.UUID
    scenario: ScenarioCreateRequest


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RiskReductionDetail(BaseModel):
    pollutant: str
    before: float
    after: float
    reduction: float


class ComplianceImpact(BaseModel):
    pollutant: str
    was_compliant: bool
    now_compliant: bool


class ScenarioResult(BaseModel):
    """Projected outcome of a single scenario."""

    name: str
    total_cost_chf: float
    total_duration_months: float
    risk_reductions: list[RiskReductionDetail]
    overall_risk_reduction: float
    compliance_impacts: list[ComplianceImpact]
    compliance_score_before: float
    compliance_score_after: float

    model_config = ConfigDict(from_attributes=True)


class CompareResponse(BaseModel):
    """Side-by-side comparison of multiple scenarios."""

    building_id: uuid.UUID
    scenarios: list[ScenarioResult]
    recommended_index: int
    recommendation_reason: str


class OptimalScenarioResponse(BaseModel):
    """Auto-generated optimal scenario."""

    building_id: uuid.UUID
    scenario: ScenarioResult
    interventions_selected: list[InterventionConfig]
    budget_used_chf: float
    budget_remaining_chf: float
    time_used_months: float


class SensitivityVariant(BaseModel):
    label: str
    total_cost_chf: float
    total_duration_months: float
    overall_risk_reduction: float


class SensitivityResponse(BaseModel):
    """Sensitivity analysis result."""

    building_id: uuid.UUID
    base_scenario: ScenarioResult
    cost_plus_20: SensitivityVariant
    cost_minus_20: SensitivityVariant
    time_plus_30: SensitivityVariant
    time_minus_30: SensitivityVariant
    removal_variants: list[SensitivityVariant]
    robustness_score: float = Field(ge=0.0, le=1.0)
