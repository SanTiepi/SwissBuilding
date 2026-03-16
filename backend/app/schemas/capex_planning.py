"""Schemas for CAPEX planning: building plans, reserve funds, investment forecasts, portfolio summaries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Line item
# ---------------------------------------------------------------------------


class CapexLineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str = "remediation"  # diagnostic | remediation | monitoring | verification | contingency
    description: str = ""
    estimated_cost: float = 0.0
    priority: str = "medium"  # critical | high | medium | low
    pollutant_type: str | None = None
    timeline_quarter: str | None = None


# ---------------------------------------------------------------------------
# FN1 — Building CAPEX plan
# ---------------------------------------------------------------------------


class BuildingCapexPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    total_estimated: float = 0.0
    total_by_category: dict[str, float] = Field(default_factory=dict)
    total_by_priority: dict[str, float] = Field(default_factory=dict)
    line_items: list[CapexLineItem] = Field(default_factory=list)
    planning_horizon_years: int = 5
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN2 — Reserve fund status
# ---------------------------------------------------------------------------


class ReserveFundStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    recommended_annual_reserve: float = 0.0
    current_gap: float = 0.0
    adequacy_rating: str = "marginal"  # adequate | marginal | insufficient | critical
    breakdown: dict[str, float] = Field(default_factory=dict)
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN3 — Investment scenarios
# ---------------------------------------------------------------------------


class InvestmentScenario(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_name: str = ""
    total_cost: float = 0.0
    risk_reduction_pct: float = 0.0
    compliance_improvement: str = ""
    payback_years: float | None = None
    recommended: bool = False


class BuildingInvestmentForecast(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    scenarios: list[InvestmentScenario] = Field(default_factory=list)
    recommended_scenario: str = ""
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN4 — Portfolio CAPEX summary
# ---------------------------------------------------------------------------


class PortfolioCapexSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int = 0
    total_capex_estimated: float = 0.0
    by_category: dict[str, float] = Field(default_factory=dict)
    by_priority: dict[str, float] = Field(default_factory=dict)
    buildings_needing_urgent_investment: int = 0
    average_reserve_adequacy: str = "marginal"
    generated_at: datetime
