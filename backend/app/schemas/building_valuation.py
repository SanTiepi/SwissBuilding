"""Schemas for building valuation — pollutant impact on Swiss building value."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# FN1 — Pollutant impact on valuation
# ---------------------------------------------------------------------------


class AffectedArea(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone: str = ""
    pollutant: str = ""
    severity: str = "unknown"


class PollutantImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    estimated_remediation_cost: float = 0.0
    value_reduction_percentage: float = 0.0
    affected_areas: list[AffectedArea] = Field(default_factory=list)
    market_impact_assessment: str = "minor"
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN2 — Renovation ROI
# ---------------------------------------------------------------------------


class RiskReduction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    before: str = "unknown"
    after: str = "low"


class RenovationROIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    total_remediation_cost: float = 0.0
    estimated_value_increase: float = 0.0
    roi_percentage: float = 0.0
    payback_period_years: float = 0.0
    risk_reduction: RiskReduction = Field(default_factory=RiskReduction)
    certification_eligibility_gained: list[str] = Field(default_factory=list)
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN3 — Market position comparison
# ---------------------------------------------------------------------------


class MarketPositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    percentile_rank: float = 50.0
    advantages: list[str] = Field(default_factory=list)
    disadvantages: list[str] = Field(default_factory=list)
    comparable_buildings_count: int = 0
    average_risk_in_area: str = "unknown"
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN4 — Portfolio valuation summary
# ---------------------------------------------------------------------------


class BuildingsByImpact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    minor: int = 0
    moderate: int = 0
    significant: int = 0
    severe: int = 0


class PriorityBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str = ""
    remediation_cost: float = 0.0
    value_impact_pct: float = 0.0
    market_impact: str = "minor"


class PortfolioValuationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_remediation_liability: float = 0.0
    average_value_impact_pct: float = 0.0
    buildings_by_impact: BuildingsByImpact = Field(default_factory=BuildingsByImpact)
    top_priority_buildings: list[PriorityBuilding] = Field(default_factory=list)
    generated_at: datetime
