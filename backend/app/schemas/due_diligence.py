"""
SwissBuildingOS - Due Diligence Schemas

Pydantic v2 schemas for buyer/investor due diligence reports on buildings
with pollutant exposure, transaction risk assessment, and acquisition comparison.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DueDiligenceRecommendation(StrEnum):
    proceed = "proceed"
    proceed_with_conditions = "proceed_with_conditions"
    defer = "defer"
    avoid = "avoid"


class RiskProbability(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    very_high = "very_high"


class RiskImpact(StrEnum):
    negligible = "negligible"
    moderate = "moderate"
    significant = "significant"
    severe = "severe"


# --- Due Diligence Report ---


class PollutantStatus(BaseModel):
    pollutant: str
    detected: bool
    risk_level: str
    sample_count: int
    threshold_exceeded: bool


class ComplianceState(BaseModel):
    diagnostic_required: bool
    diagnostic_completed: bool
    waste_plan_required: bool
    suva_notification_required: bool
    canton: str
    authority_name: str


class RemediationCostSummary(BaseModel):
    total_min_chf: float
    total_max_chf: float
    pollutant_count: int
    primary_cost_driver: str | None = None


class RiskFlag(BaseModel):
    flag: str
    severity: str  # low, medium, high, critical
    description: str


class PropertyValueImpactSummary(BaseModel):
    total_depreciation_pct: float
    post_remediation_recovery_pct: float
    net_impact_pct: float


class DueDiligenceReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    city: str
    canton: str
    construction_year: int | None
    building_type: str
    surface_area_m2: float | None
    pollutant_statuses: list[PollutantStatus]
    compliance_state: ComplianceState
    remediation_cost: RemediationCostSummary
    risk_flags: list[RiskFlag]
    value_impact: PropertyValueImpactSummary
    recommendation: DueDiligenceRecommendation
    recommendation_rationale: str
    generated_at: datetime


# --- Transaction Risks ---


class TransactionRisk(BaseModel):
    category: str  # regulatory, financial, legal, reputational
    title: str
    description: str
    probability: RiskProbability
    impact: RiskImpact
    mitigation: str
    contributing_pollutants: list[str]


class TransactionRiskAssessment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    overall_risk_score: float  # 0.0 - 1.0
    risks: list[TransactionRisk]
    highest_risk_category: str
    summary: str


# --- Property Value Impact ---


class PollutantDepreciation(BaseModel):
    pollutant: str
    detected: bool
    base_depreciation_pct: float
    applied_depreciation_pct: float


class PropertyValueImpact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    pollutant_depreciations: list[PollutantDepreciation]
    raw_cumulative_pct: float
    capped_depreciation_pct: float
    post_remediation_recovery_pct: float
    net_impact_pct: float
    summary: str


# --- Acquisition Comparison ---


class AcquisitionTarget(BaseModel):
    building_id: UUID
    address: str
    risk_score: float
    remediation_cost_chf: float
    value_impact_pct: float
    recommendation: DueDiligenceRecommendation
    rank: int


class AcquisitionCompareRequest(BaseModel):
    building_ids: list[UUID]


class AcquisitionCompareResponse(BaseModel):
    targets: list[AcquisitionTarget]
    best_target: UUID | None = None
    worst_target: UUID | None = None
