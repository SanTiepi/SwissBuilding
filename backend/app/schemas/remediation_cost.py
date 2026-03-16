"""Schemas for remediation cost estimation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PollutantCostBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    work_category: str | None = None
    affected_area_m2: float = 0.0
    unit_cost_chf: float = 0.0
    subtotal_chf: float = 0.0
    waste_surcharge_chf: float = 0.0
    sample_count: int = 0
    lab_cost_chf: float = 0.0


class RemediationCostEstimate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    pollutant_breakdowns: list[PollutantCostBreakdown] = Field(default_factory=list)
    total_min_chf: float = 0.0
    total_max_chf: float = 0.0
    waste_cost_chf: float = 0.0
    safety_cost_chf: float = 0.0
    lab_cost_chf: float = 0.0
    timeline_weeks_estimate: int = 0
    generated_at: datetime


class BuildingCostComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    total_estimate_chf: float = 0.0
    cost_per_m2: float = 0.0
    rank: int = 0
    primary_cost_driver: str | None = None


class CostFactors(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    age_factor: float = 1.0
    floors_factor: float = 1.0
    pollutant_count: int = 0
    surface_area_m2: float = 0.0
    urgency_flags: list[str] = Field(default_factory=list)


class CompareRequest(BaseModel):
    building_ids: list[UUID] = Field(..., max_length=10)
