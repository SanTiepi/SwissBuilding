"""Pydantic v2 schemas for the Energy Performance service."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnergyPerformanceEstimate(BaseModel):
    """Energy performance for a single building (real CECB or estimated)."""

    building_id: UUID
    energy_class: str = Field(..., pattern=r"^[A-G]$")
    kwh_per_m2_year: float
    co2_kg_per_m2_year: float
    total_co2_kg_year: float
    improvement_potential_class: str | None = None
    minergie_compatible: bool
    factors: list[str]
    source: str = Field(default="estimated", description="'cecb' or 'estimated'")
    cecb_heating_demand: float | None = None
    cecb_cooling_demand: float | None = None
    cecb_dhw_demand: float | None = None
    estimated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RenovationImpactRequest(BaseModel):
    """Request body for renovation impact projection."""

    planned_interventions: list[str]


class RenovationEnergyImpact(BaseModel):
    """Projected energy impact of planned interventions."""

    building_id: UUID
    current_class: str
    projected_class: str
    energy_savings_percent: float
    co2_reduction_kg: float
    annual_savings_chf: float
    planned_interventions: list[str]

    model_config = ConfigDict(from_attributes=True)


class PortfolioEnergyProfile(BaseModel):
    """Aggregate energy profile across a portfolio of buildings."""

    total_buildings: int
    class_distribution: dict[str, int]
    total_co2_tonnes_year: float
    avg_kwh_per_m2: float
    worst_performers: list[dict]
    improvement_potential_summary: str

    model_config = ConfigDict(from_attributes=True)


class BuildingEnergyComparison(BaseModel):
    """Energy comparison entry for a single building."""

    building_id: UUID
    address: str
    energy_class: str
    kwh_per_m2_year: float
    co2_kg_per_m2_year: float
    rank: int

    model_config = ConfigDict(from_attributes=True)


class CompareRequest(BaseModel):
    """Request body for building energy comparison."""

    building_ids: list[UUID] = Field(..., max_length=10)
