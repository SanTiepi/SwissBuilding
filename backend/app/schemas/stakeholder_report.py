"""Pydantic v2 schemas for stakeholder-specific reports."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Owner report
# ---------------------------------------------------------------------------


class OwnerRiskOverview(BaseModel):
    """Plain-language risk summary for owners."""

    pollutant: str
    risk_level: str  # low | medium | high | critical
    plain_language: str  # e.g. "Probable presence of asbestos in the building"

    model_config = ConfigDict(from_attributes=True)


class OwnerFinancialImpact(BaseModel):
    """Cost estimates for the owner."""

    estimated_total_chf: float
    cost_range_low_chf: float
    cost_range_high_chf: float
    breakdown: list[dict] | None = None  # [{category, amount}]

    model_config = ConfigDict(from_attributes=True)


class OwnerActionPlanItem(BaseModel):
    """Single recommended action for owner."""

    title: str
    priority: str
    description: str | None = None
    due_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OwnerReport(BaseModel):
    """Owner-facing building report: plain language, no jargon."""

    building_id: UUID
    generated_at: datetime
    executive_summary: str
    risk_overview: list[OwnerRiskOverview]
    financial_impact: OwnerFinancialImpact
    action_plan: list[OwnerActionPlanItem]
    next_steps: list[str]

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Authority report
# ---------------------------------------------------------------------------


class AuthorityPollutantStatus(BaseModel):
    """Per-pollutant compliance status for authority."""

    pollutant: str
    has_diagnostic: bool
    sample_count: int
    threshold_exceeded: bool
    max_concentration: float | None = None
    unit: str | None = None
    legal_threshold: float | None = None
    legal_reference: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuthorityArtefactStatus(BaseModel):
    """Compliance artefact status."""

    artefact_type: str
    status: str
    title: str
    submitted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AuthorityReport(BaseModel):
    """Authority-facing: regulatory compliance per pollutant."""

    building_id: UUID
    generated_at: datetime
    overall_compliance_status: str  # compliant | non_compliant | partial | unknown
    diagnostic_coverage: dict[str, bool]  # {pollutant: has_diagnostic}
    pollutant_statuses: list[AuthorityPollutantStatus]
    artefact_statuses: list[AuthorityArtefactStatus]
    deadline_compliance: str  # on_track | overdue | no_deadlines

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Contractor briefing
# ---------------------------------------------------------------------------


class ContractorPollutantLocation(BaseModel):
    """Location info for pollutant presence, contractor-relevant."""

    pollutant: str
    location_floor: str | None = None
    location_room: str | None = None
    location_detail: str | None = None
    material_description: str | None = None
    concentration: float | None = None
    unit: str | None = None
    cfst_work_category: str | None = None
    waste_disposal_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ContractorSafetyRequirement(BaseModel):
    """CFST 6503 safety category for contractor."""

    category: str  # minor | medium | major
    description: str
    pollutants: list[str]

    model_config = ConfigDict(from_attributes=True)


class ContractorBriefing(BaseModel):
    """Contractor-facing: work scope, pollutant locations, safety."""

    building_id: UUID
    generated_at: datetime
    work_scope_summary: str
    pollutant_locations: list[ContractorPollutantLocation]
    safety_requirements: list[ContractorSafetyRequirement]
    access_constraints: list[str]
    estimated_quantities: dict[str, int]  # {pollutant: sample_count}

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Portfolio executive summary
# ---------------------------------------------------------------------------


class PortfolioKPIs(BaseModel):
    """C-level KPIs for portfolio."""

    total_buildings: int
    buildings_at_risk: int
    compliance_percentage: float
    estimated_total_cost_chf: float

    model_config = ConfigDict(from_attributes=True)


class PortfolioPriorityBuilding(BaseModel):
    """Top-priority building in portfolio."""

    building_id: UUID
    address: str
    city: str
    risk_level: str
    open_actions: int

    model_config = ConfigDict(from_attributes=True)


class PortfolioExecutiveSummary(BaseModel):
    """C-level portfolio summary with KPIs and top priorities."""

    organization_id: UUID
    generated_at: datetime
    kpis: PortfolioKPIs
    top_priorities: list[PortfolioPriorityBuilding]
    trend_arrows: dict[str, str]  # {metric: "up" | "down" | "stable"}

    model_config = ConfigDict(from_attributes=True)
