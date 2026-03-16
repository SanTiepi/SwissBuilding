"""Pydantic schemas for handoff pack generation."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HandoffSection(BaseModel):
    """A single section within a handoff pack."""

    section_name: str
    section_type: str
    items: list[dict[str, Any]]
    completeness: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DiagnosticHandoffResult(BaseModel):
    """Handoff pack from diagnostician to property manager."""

    building_id: uuid.UUID
    generated_at: datetime
    findings_summary: HandoffSection
    risk_levels: HandoffSection
    recommended_actions: HandoffSection
    cost_estimates: HandoffSection
    regulatory_obligations: HandoffSection
    timeline: HandoffSection
    overall_completeness: float = Field(ge=0.0, le=1.0)
    warnings: list[str]

    model_config = ConfigDict(from_attributes=True)


class ContractorHandoffResult(BaseModel):
    """Handoff pack from property manager to contractor."""

    building_id: uuid.UUID
    generated_at: datetime
    work_scope: HandoffSection
    pollutant_map: HandoffSection
    safety_requirements: HandoffSection
    access_constraints: HandoffSection
    material_quantities: HandoffSection
    disposal_requirements: HandoffSection
    reference_documents: HandoffSection
    overall_completeness: float = Field(ge=0.0, le=1.0)
    warnings: list[str]

    model_config = ConfigDict(from_attributes=True)


class AuthorityHandoffResult(BaseModel):
    """Handoff pack from property manager to authority."""

    building_id: uuid.UUID
    generated_at: datetime
    compliance_status: HandoffSection
    diagnostic_reports: HandoffSection
    remediation_plan: HandoffSection
    waste_management: HandoffSection
    responsible_parties: HandoffSection
    timeline_commitments: HandoffSection
    overall_completeness: float = Field(ge=0.0, le=1.0)
    warnings: list[str]

    model_config = ConfigDict(from_attributes=True)


class HandoffValidationWarning(BaseModel):
    """A single validation warning for a handoff pack."""

    field: str
    message: str
    severity: str  # "error" | "warning" | "info"


class HandoffValidationResult(BaseModel):
    """Result of validating handoff completeness."""

    building_id: uuid.UUID
    handoff_type: str
    readiness_score: int = Field(ge=0, le=100)
    missing_fields: list[str]
    incomplete_sections: list[str]
    quality_warnings: list[HandoffValidationWarning]
    is_ready: bool

    model_config = ConfigDict(from_attributes=True)
