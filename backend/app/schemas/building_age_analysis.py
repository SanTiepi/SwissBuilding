"""Schemas for building age analysis — era classification and pollutant probability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PollutantProbability(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant: str
    probability: str  # high / medium / low / negligible
    typical_materials: list[str] = Field(default_factory=list)
    notes: str | None = None


class EraClassification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    construction_year: int | None = None
    era: str  # pre_1950 / 1950_1975 / 1975_1991 / post_1991 / unknown
    era_label: str
    pollutant_probabilities: list[PollutantProbability]
    diagnostic_priority: str  # critical / high / medium / low
    summary: str
    generated_at: datetime


class RiskModifier(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    factor: str
    impact: str  # increases / decreases / neutral
    description: str


class AgeBasedRiskProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    construction_year: int | None = None
    era: str
    baseline_risk: str  # elevated / moderate / low
    has_diagnostics: bool
    diagnostic_count: int
    completed_diagnostic_count: int
    risk_modifiers: list[RiskModifier]
    overall_risk: str  # elevated / moderate / low
    recommendation: str
    generated_at: datetime


class EraHotspot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone_type: str
    element_type: str
    pollutant: str
    probability: str  # high / medium / low
    description: str
    matched_zone_id: UUID | None = None
    matched_zone_name: str | None = None


class EraHotspotReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    construction_year: int | None = None
    era: str
    hotspots: list[EraHotspot]
    total_matched_zones: int
    generated_at: datetime


class EraBucket(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    era: str
    era_label: str
    building_count: int
    diagnosed_count: int
    undiagnosed_count: int
    avg_diagnostic_priority: str | None = None


class PriorityBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    construction_year: int | None = None
    era: str
    diagnostic_count: int


class PortfolioAgeDistribution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int
    era_buckets: list[EraBucket]
    priority_buildings: list[PriorityBuilding]
    generated_at: datetime
