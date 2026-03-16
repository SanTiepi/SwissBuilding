"""
SwissBuildingOS - Insurance Risk Assessment Schemas

Pydantic v2 schemas for insurance risk evaluation of pollutant-containing buildings.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InsuranceRiskTier(StrEnum):
    standard = "standard"
    elevated = "elevated"
    high = "high"
    uninsurable = "uninsurable"


class CoverageRestriction(BaseModel):
    restriction_type: str
    description: str
    pollutant: str | None = None


class RequiredMitigation(BaseModel):
    action: str
    priority: str  # immediate, short_term, medium_term
    pollutant: str | None = None
    estimated_cost_chf: float | None = None


class InsuranceRiskAssessment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    risk_tier: InsuranceRiskTier
    premium_impact_multiplier: float
    pollutant_flags: dict[str, str]  # pollutant -> risk_level
    coverage_restrictions: list[CoverageRestriction]
    required_mitigations: list[RequiredMitigation]
    has_diagnostic: bool
    building_year: int | None
    summary: str


class LiabilityCategory(BaseModel):
    category: str  # occupant_health, worker_safety, environmental_contamination, remediation_cost
    score: float  # 0.0 - 1.0
    justification: str
    contributing_pollutants: list[str]


class LiabilityExposure(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    overall_liability_score: float
    categories: list[LiabilityCategory]
    highest_risk_category: str
    summary: str


class InsuranceProfileComparison(BaseModel):
    building_id: UUID
    address: str
    risk_tier: InsuranceRiskTier
    premium_impact_multiplier: float
    worst_pollutant: str | None
    recommended_actions: list[str]


class InsuranceCompareRequest(BaseModel):
    building_ids: list[UUID]


class InsuranceCompareResponse(BaseModel):
    profiles: list[InsuranceProfileComparison]
    best_tier: InsuranceRiskTier
    worst_tier: InsuranceRiskTier


class TierDistribution(BaseModel):
    standard: int = 0
    elevated: int = 0
    high: int = 0
    uninsurable: int = 0


class PortfolioInsuranceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int
    assessed_buildings: int
    tier_distribution: TierDistribution
    average_premium_multiplier: float
    total_premium_impact: float
    buildings_requiring_immediate_action: int
    trend_indicator: str  # improving, stable, worsening
    summary: str
