"""Schemas for cost-benefit analysis of remediation interventions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# FN1 — Intervention ROI
# ---------------------------------------------------------------------------


class InterventionROI(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    risk_level: str | None = None
    estimated_cost_chf: float = 0.0
    risk_reduction_value_chf: float = 0.0
    roi_ratio: float = 0.0
    payback_years: float = 0.0
    npv_chf: float = 0.0
    priority_score: float = 0.0


class InterventionROIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    interventions: list[InterventionROI] = Field(default_factory=list)
    discount_rate: float = 0.03
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN2 — Remediation strategies
# ---------------------------------------------------------------------------


class RemediationStrategy(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy: str  # minimal | standard | comprehensive
    description: str = ""
    total_cost_chf: float = 0.0
    risk_reduction_pct: float = 0.0
    timeline_weeks: int = 0
    residual_risk_level: str = "unknown"
    pollutants_addressed: list[str] = Field(default_factory=list)


class RemediationStrategiesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    strategies: list[RemediationStrategy] = Field(default_factory=list)
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN3 — Inaction cost
# ---------------------------------------------------------------------------


class InactionCost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    regulatory_fine_min_chf: float = 0.0
    regulatory_fine_max_chf: float = 0.0
    liability_exposure_chf_per_year: float = 0.0
    insurance_premium_increase_pct: float = 0.0
    property_depreciation_pct: float = 0.0
    total_inaction_cost_year1_chf: float = 0.0
    total_inaction_cost_year5_chf: float = 0.0
    pollutant_details: list[PollutantInactionDetail] = Field(default_factory=list)
    generated_at: datetime


class PollutantInactionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    risk_level: str | None = None
    depreciation_pct: float = 0.0
    fine_range_min_chf: float = 0.0
    fine_range_max_chf: float = 0.0


# Forward-ref update for InactionCost
InactionCost.model_rebuild()


# ---------------------------------------------------------------------------
# FN4 — Portfolio investment plan
# ---------------------------------------------------------------------------


class BuildingInvestmentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str = ""
    estimated_cost_chf: float = 0.0
    risk_score: float = 0.0
    risk_reduction_pct: float = 0.0
    cumulative_cost_chf: float = 0.0
    cumulative_risk_reduction_pct: float = 0.0
    rank: int = 0


class BudgetBreakpoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_chf: float = 0.0
    buildings_covered: int = 0
    risk_reduction_pct: float = 0.0


class PortfolioInvestmentPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    ranked_buildings: list[BuildingInvestmentItem] = Field(default_factory=list)
    budget_breakpoints: list[BudgetBreakpoint] = Field(default_factory=list)
    total_portfolio_cost_chf: float = 0.0
    total_risk_reduction_pct: float = 0.0
    generated_at: datetime
