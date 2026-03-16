"""Pydantic v2 schemas for the Regulatory Change Impact Analyzer."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RegulationChange(BaseModel):
    """A single proposed regulatory threshold change."""

    pollutant: str
    measurement_type: str = "material_content"
    new_threshold: float
    unit: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ThresholdChangeRequest(BaseModel):
    """Request body for single threshold change simulation."""

    pollutant: str
    measurement_type: str = "material_content"
    new_threshold: float
    unit: str | None = None
    org_id: UUID | None = None


class MultiChangeRequest(BaseModel):
    """Request body for multi-regulation impact analysis."""

    changes: list[RegulationChange]
    org_id: UUID | None = None


class AffectedBuilding(BaseModel):
    """A building affected by a regulatory change."""

    building_id: UUID
    address: str
    city: str
    canton: str
    pollutant: str
    current_concentration: float
    current_threshold: float
    new_threshold: float
    margin_percent: float = Field(description="How far above the new threshold (percent)")
    was_compliant: bool
    becomes_non_compliant: bool

    model_config = ConfigDict(from_attributes=True)


class ThresholdChangeSimulation(BaseModel):
    """Result of a single threshold change simulation."""

    pollutant: str
    measurement_type: str
    current_threshold: float
    new_threshold: float
    unit: str
    legal_ref: str | None = None
    total_buildings_analyzed: int
    currently_non_compliant: int
    newly_non_compliant: int
    total_non_compliant_after: int
    affected_buildings: list[AffectedBuilding]
    estimated_additional_remediation_cost_chf: float

    model_config = ConfigDict(from_attributes=True)


class MultiChangeImpact(BaseModel):
    """Result of multi-regulation impact analysis."""

    changes: list[ThresholdChangeSimulation]
    total_buildings_analyzed: int
    buildings_affected_by_any_change: int
    buildings_affected_by_multiple_changes: int
    total_estimated_cost_chf: float

    model_config = ConfigDict(from_attributes=True)


class PollutantSensitivity(BaseModel):
    """Sensitivity of a building to threshold changes for one pollutant."""

    pollutant: str
    measurement_type: str
    current_threshold: float
    unit: str
    max_concentration: float | None = None
    margin_percent: float | None = Field(
        None,
        description="Margin below threshold (positive = compliant, negative = non-compliant)",
    )
    is_currently_compliant: bool
    non_compliant_if_threshold_drops_10_pct: bool
    non_compliant_if_threshold_drops_20_pct: bool
    non_compliant_if_threshold_drops_50_pct: bool
    sample_count: int

    model_config = ConfigDict(from_attributes=True)


class BuildingRegulatorySensitivity(BaseModel):
    """Full regulatory sensitivity profile for a building."""

    building_id: UUID
    address: str
    city: str
    canton: str
    sensitivities: list[PollutantSensitivity]
    overall_vulnerability: str  # low, medium, high, critical

    model_config = ConfigDict(from_attributes=True)


class VulnerableBuilding(BaseModel):
    """A building ranked by compliance vulnerability."""

    building_id: UUID
    address: str
    city: str
    canton: str
    closest_margin_percent: float | None = None
    closest_margin_pollutant: str | None = None
    pollutants_near_threshold: int
    vulnerability_score: float = Field(description="0-100, higher = more vulnerable")

    model_config = ConfigDict(from_attributes=True)


class ComplianceForecast(BaseModel):
    """Portfolio compliance forecast."""

    org_id: UUID | None = None
    total_buildings: int
    buildings_with_samples: int
    currently_non_compliant: int
    vulnerable_buildings: list[VulnerableBuilding]
    risk_summary: dict[str, int] = Field(description="Count of buildings per vulnerability level")

    model_config = ConfigDict(from_attributes=True)
