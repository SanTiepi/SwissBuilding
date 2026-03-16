"""Pydantic v2 schemas for the Environmental Impact service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RiskCategory(BaseModel):
    """A single environmental risk category assessment."""

    category: str
    level: str = Field(..., pattern=r"^(low|medium|high)$")
    score: float = Field(..., ge=0.0, le=1.0)
    justification: str

    model_config = ConfigDict(from_attributes=True)


class EnvironmentalImpactAssessment(BaseModel):
    """Environmental risk assessment for a building based on pollutant context."""

    building_id: UUID
    soil_contamination: RiskCategory
    water_table_risk: RiskCategory
    air_quality_impact: RiskCategory
    neighborhood_exposure: RiskCategory
    overall_level: str
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmissionDetail(BaseModel):
    """Detail for a single remediation emission source."""

    source: str
    co2_kg: float
    description: str

    model_config = ConfigDict(from_attributes=True)


class RemediationFootprint(BaseModel):
    """Environmental cost of the remediation process itself."""

    building_id: UUID
    waste_transport_co2_kg: float
    disposal_emissions_co2_kg: float
    dust_fiber_release_risk: str
    temporary_contamination_risk: str
    total_remediation_co2_kg: float
    avoided_long_term_co2_kg: float
    net_environmental_balance_co2_kg: float
    emission_details: list[EmissionDetail]
    estimated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GreenScoreSubCategory(BaseModel):
    """Sub-category within the green building score."""

    name: str
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float
    details: str

    model_config = ConfigDict(from_attributes=True)


class GreenBuildingScore(BaseModel):
    """Composite green building score for a single building."""

    building_id: UUID
    overall_score: float = Field(..., ge=0.0, le=100.0)
    grade: str
    sub_categories: list[GreenScoreSubCategory]
    recommendations: list[str]
    scored_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingGreenSummary(BaseModel):
    """Summary of a building's green score for portfolio reports."""

    building_id: UUID
    address: str
    overall_score: float
    grade: str

    model_config = ConfigDict(from_attributes=True)


class ImprovementOpportunity(BaseModel):
    """An identified environmental improvement opportunity."""

    building_id: UUID
    address: str
    current_score: float
    potential_score: float
    action: str

    model_config = ConfigDict(from_attributes=True)


class PortfolioEnvironmentalReport(BaseModel):
    """Organization-level environmental report."""

    org_id: UUID | None
    total_buildings: int
    total_environmental_footprint_co2_kg: float
    avg_green_score: float
    grade_distribution: dict[str, int]
    top_performers: list[BuildingGreenSummary]
    worst_performers: list[BuildingGreenSummary]
    improvement_opportunities: list[ImprovementOpportunity]
    regulatory_compliance_rate: float
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
