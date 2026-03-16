"""Schemas for portfolio optimization endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BuildingPriority(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    city: str
    canton: str
    risk_score: float = Field(ge=0, le=100)
    urgency_score: float = Field(ge=0, le=100)
    impact_score: float = Field(ge=0, le=100)
    roi_score: float = Field(ge=0)
    combined_score: float = Field(ge=0)
    rank: int = Field(ge=1)
    recommended_budget_chf: float | None = None


class PortfolioPrioritization(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_buildings: int
    total_estimated_cost_chf: float
    budget_chf: float | None = None
    prioritized_buildings: list[BuildingPriority]
    budget_coverage_percent: float | None = None


class BuildingActionRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    recommended_actions: list[str]
    estimated_cost_chf: float
    priority_rank: int
    timeline_weeks: int


class PortfolioActionPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_buildings_analyzed: int
    action_plan: list[BuildingActionRecommendation]
    total_estimated_cost_chf: float
    total_timeline_weeks: int


class RiskDistributionAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    by_canton: dict[str, float]
    by_building_type: dict[str, float]
    by_decade: dict[str, float]
    by_pollutant: dict[str, float]
    highest_risk_cluster: str


class BuildingBudgetAllocation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    allocated_chf: float
    percent_of_budget: float
    expected_risk_reduction: float


class BudgetAllocationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_budget_chf: float
    allocations: list[BuildingBudgetAllocation]
    expected_portfolio_risk_reduction: float
    unallocated_chf: float


class BudgetAllocationRequest(BaseModel):
    building_ids: list[UUID]
    total_budget_chf: float = Field(gt=0)
