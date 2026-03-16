"""Schemas for compliance gap analysis."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ComplianceGapItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    regulation_ref: str
    regulation_name: str
    current_state: str
    required_state: str
    severity: str  # low | medium | high | critical
    remediation_path: str
    sample_count: int = 0


class ComplianceGapReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    total_gaps: int = 0
    gaps: list[ComplianceGapItem] = Field(default_factory=list)
    compliant_regulations: list[str] = Field(default_factory=list)
    generated_at: datetime


class RoadmapStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_number: int
    title: str
    description: str
    pollutant_type: str
    regulation_ref: str
    dependencies: list[int] = Field(default_factory=list)
    estimated_weeks: int = 0
    responsible_party: str
    estimated_cost_chf: float = 0.0
    is_critical_path: bool = False


class ComplianceRoadmap(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    steps: list[RoadmapStep] = Field(default_factory=list)
    total_weeks: int = 0
    critical_path_weeks: int = 0
    generated_at: datetime


class CostRange(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    min_chf: float = 0.0
    expected_chf: float = 0.0
    max_chf: float = 0.0


class RegulationCostBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regulation_ref: str
    regulation_name: str
    cost: CostRange


class PollutantCostBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    cost: CostRange


class LaborMaterialsDisposal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    labor_chf: CostRange
    materials_chf: CostRange
    disposal_chf: CostRange


class ComplianceCostEstimate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    total: CostRange
    by_regulation: list[RegulationCostBreakdown] = Field(default_factory=list)
    by_pollutant: list[PollutantCostBreakdown] = Field(default_factory=list)
    by_category: LaborMaterialsDisposal
    generated_at: datetime


class PortfolioBuildingGap(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    gap_count: int = 0
    estimated_cost_chf: float = 0.0
    worst_severity: str = "low"


class GapTypeCount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regulation_ref: str
    regulation_name: str
    count: int = 0


class PortfolioComplianceGaps(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int = 0
    buildings_with_gaps: int = 0
    total_gap_count: int = 0
    estimated_total_cost_chf: float = 0.0
    most_common_gaps: list[GapTypeCount] = Field(default_factory=list)
    furthest_from_compliance: list[PortfolioBuildingGap] = Field(default_factory=list)
    generated_at: datetime
