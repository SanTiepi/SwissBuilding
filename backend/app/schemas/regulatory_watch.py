"""Pydantic schemas for the Regulatory Watch module."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class RegulationInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regulation_name: str
    reference: str
    domain: str
    effective_date: date
    thresholds: dict
    enforcement_level: str  # strict | moderate | advisory


class ComplianceGap(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regulation: str
    gap_description: str
    remediation_required: bool


class AffectedSample(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sample_id: UUID
    current_value: float
    new_threshold: float


class MostImpactedBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str | None = None
    canton: str | None = None
    gap_count: int
    estimated_cost: float


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ActiveRegulationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    canton: str
    regulations: list[RegulationInfo]


class RegulatoryImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    applicable_regulations: list[str]
    compliance_gaps: list[ComplianceGap]
    overall_exposure: str  # low | medium | high
    estimated_compliance_cost: float


class ThresholdSimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    pollutant_type: str
    currently_compliant: bool
    would_be_compliant: bool
    affected_samples: list[AffectedSample]
    additional_remediation_needed: bool
    cost_delta: float


class ExposureByDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    domain: str
    buildings_affected: int
    total_cost: float


class PortfolioExposureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: UUID
    regulations_tracked: int
    buildings_with_gaps: int
    total_compliance_cost: float
    exposure_by_domain: list[ExposureByDomain]
    most_impacted_buildings: list[MostImpactedBuilding]
