"""Pydantic v2 schemas for Work-Family Trade Matrix API."""

from __future__ import annotations

from pydantic import BaseModel


class WorkFamilyRead(BaseModel):
    """A single work family definition."""

    name: str
    label_fr: str
    pollutant: str | None = None
    procedures: list[str]
    procedure_names: list[str]
    authorities: list[str]
    proof_required: list[str]
    contractor_categories: list[str]
    safe_to_x_implications: list[str]
    cfst_category: str | None = None
    regulatory_basis: str


class WorkFamilyRequirement(BaseModel):
    """A work family's resolved requirements for a specific case."""

    name: str
    label_fr: str
    applicable_procedures: list[str]
    required_proof: list[str]
    authorities_to_notify: list[str]
    safe_to_x_implications: list[str]
    contractor_requirements: list[str]
    regulatory_basis: str


class WorkFamilyRequirementsAggregate(BaseModel):
    """Aggregated requirements across all families."""

    all_procedures: list[str]
    all_proof: list[str]
    all_authorities: list[str]
    all_safe_to_x: list[str]


class CaseWorkFamilyRequirements(BaseModel):
    """Full requirements response for a BuildingCase."""

    case_id: str
    case_type: str | None = None
    building_id: str | None = None
    work_families: list[WorkFamilyRequirement] = []
    aggregate: WorkFamilyRequirementsAggregate | None = None
    error: str | None = None


class WorkFamilyCoverageItem(BaseModel):
    """Coverage status for a single work family."""

    label_fr: str
    procedures_ready: list[str]
    procedures_missing: list[str]
    proof_available: list[str]
    proof_missing: list[str]
    safe_to_x_status: dict[str, str]
    coverage_pct: float


class WorkFamilyCoverageSummary(BaseModel):
    """Summary of coverage across all families."""

    total_families: int
    families_fully_covered: int
    families_partial: int
    families_uncovered: int
    overall_coverage_pct: float


class BuildingWorkFamilyCoverage(BaseModel):
    """Full coverage response for a building."""

    building_id: str
    families: dict[str, WorkFamilyCoverageItem] = {}
    summary: WorkFamilyCoverageSummary | None = None
    error: str | None = None
