"""Schemas for budget tracking: overview, variance, forecast, portfolio summary."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# FN1 — Building budget overview
# ---------------------------------------------------------------------------


class BudgetOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    estimated_total_cost_chf: float = 0.0
    spent_chf: float = 0.0
    remaining_chf: float = 0.0
    burn_rate_chf_per_month: float = 0.0
    projected_completion_cost_chf: float = 0.0
    variance_pct: float = 0.0
    status: str = "on_track"  # on_track | over_budget | under_budget
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN2 — Per-intervention cost variance
# ---------------------------------------------------------------------------


class InterventionCostItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intervention_id: UUID
    title: str = ""
    intervention_type: str = ""
    cost_category: str = "remediation"
    estimated_cost_chf: float = 0.0
    actual_cost_chf: float | None = None
    variance_chf: float = 0.0
    variance_pct: float = 0.0
    is_overrun: bool = False
    status: str = "planned"


class CostVarianceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    items: list[InterventionCostItem] = Field(default_factory=list)
    total_estimated_chf: float = 0.0
    total_actual_chf: float = 0.0
    total_variance_chf: float = 0.0
    overrun_count: int = 0
    by_category: dict[str, float] = Field(default_factory=dict)
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN3 — Quarterly spend forecast
# ---------------------------------------------------------------------------


class QuarterlyForecast(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quarter: str  # e.g. "2026-Q2"
    projected_spend_chf: float = 0.0
    intervention_count: int = 0
    categories: dict[str, float] = Field(default_factory=dict)


class QuarterlySpendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    quarters: list[QuarterlyForecast] = Field(default_factory=list)
    total_projected_chf: float = 0.0
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN4 — Portfolio budget summary
# ---------------------------------------------------------------------------


class BuildingBudgetItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str = ""
    estimated_cost_chf: float = 0.0
    spent_chf: float = 0.0
    remaining_chf: float = 0.0
    is_over_budget: bool = False


class PortfolioBudgetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_estimated_chf: float = 0.0
    total_spent_chf: float = 0.0
    total_remaining_chf: float = 0.0
    buildings_over_budget: int = 0
    quarterly_forecast: list[QuarterlyForecast] = Field(default_factory=list)
    risk_reduction_per_chf: float = 0.0
    buildings: list[BuildingBudgetItem] = Field(default_factory=list)
    generated_at: datetime
