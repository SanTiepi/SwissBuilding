"""Schemas for subsidy tracking: eligibility, applications, funding gaps, portfolio summary."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Subsidy program definition
# ---------------------------------------------------------------------------


class SubsidyProgram(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    program_id: str
    name: str
    provider: str  # federal | cantonal | municipal
    canton: str | None = None
    eligible_pollutants: list[str] = Field(default_factory=list)
    max_amount_chf: float = 0.0
    coverage_percentage: float = 0.0
    application_deadline: date | None = None
    requirements: list[str] = Field(default_factory=list)
    status: str = "open"  # open | closed | upcoming


# ---------------------------------------------------------------------------
# FN1 — Building subsidy eligibility
# ---------------------------------------------------------------------------


class BuildingSubsidyEligibility(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    eligible_programs: list[SubsidyProgram] = Field(default_factory=list)
    total_potential_funding: float = 0.0
    recommended_priority: list[str] = Field(default_factory=list)
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN2 — Building subsidy status (applications)
# ---------------------------------------------------------------------------


class SubsidyApplication(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    program_name: str = ""
    amount_requested: float = 0.0
    amount_approved: float | None = None
    status: str = "draft"  # draft | submitted | under_review | approved | rejected | disbursed
    submitted_date: date | None = None
    decision_date: date | None = None


class BuildingSubsidyStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    applications: list[SubsidyApplication] = Field(default_factory=list)
    total_requested: float = 0.0
    total_approved: float = 0.0
    total_disbursed: float = 0.0
    pending_count: int = 0
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN3 — Funding gap analysis
# ---------------------------------------------------------------------------


class FundingGap(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    estimated_remediation_cost: float = 0.0
    available_subsidies: float = 0.0
    gap_amount: float = 0.0
    gap_percentage: float = 0.0


class BuildingFundingGapAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    gaps: list[FundingGap] = Field(default_factory=list)
    total_remediation_cost: float = 0.0
    total_available_funding: float = 0.0
    total_gap: float = 0.0
    funding_coverage_pct: float = 0.0
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN4 — Portfolio subsidy summary
# ---------------------------------------------------------------------------


class PortfolioSubsidySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings_eligible: int = 0
    total_potential_funding: float = 0.0
    total_approved: float = 0.0
    total_gap: float = 0.0
    by_provider: dict[str, float] = Field(default_factory=dict)
    generated_at: datetime
