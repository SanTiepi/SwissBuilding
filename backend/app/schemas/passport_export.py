"""Pydantic v2 schemas for building passport export."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PassportIdentity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    egid: int | None = None
    egrid: str | None = None
    address: str
    postal_code: str
    city: str
    canton: str
    construction_year: int | None = None
    building_type: str


class PassportPollutantSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    diagnosed: bool
    sample_count: int
    exceeded_count: int
    risk_level: str
    last_diagnostic_date: date | None = None
    compliance_status: str  # compliant/non_compliant/unknown/pending


class PassportInterventionSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intervention_count: int
    completed_count: int
    planned_count: int
    total_estimated_cost: float
    intervention_types: list[str]


class PassportComplianceSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall_status: str  # compliant/non_compliant/partial/unknown
    open_actions: int
    critical_actions: int
    next_deadline: date | None = None
    regulatory_framework: str


class BuildingPassportExport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    passport_version: str
    export_format: str  # json/summary
    identity: PassportIdentity
    pollutant_sections: list[PassportPollutantSection]
    intervention_summary: PassportInterventionSection
    compliance: PassportComplianceSection
    quality_score: float
    completeness_score: float
    generated_at: datetime


class PassportComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_a_id: UUID
    building_b_id: UUID
    similarity_score: float
    matching_pollutants: list[str]
    differing_fields: list[str]
    recommendation: str


class PassportValidation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    is_valid: bool
    missing_fields: list[str]
    warnings: list[str]
    completeness_pct: float
    generated_at: datetime


class PortfolioPassportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int
    passports_complete: int
    passports_incomplete: int
    average_quality_score: float
    average_completeness: float
    buildings_needing_attention: list[str]
    generated_at: datetime
