"""Pydantic v2 schemas for Transaction Readiness evaluation."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionType(StrEnum):
    """Types of transactions a building can be evaluated for."""

    sell = "sell"
    insure = "insure"
    finance = "finance"
    lease = "lease"


class CheckStatus(StrEnum):
    """Status of an individual transaction readiness check."""

    met = "met"
    unmet = "unmet"
    partial = "partial"
    unknown = "unknown"


class CheckSeverity(StrEnum):
    """Severity of an unmet check."""

    blocker = "blocker"
    warning = "warning"
    info = "info"


class OverallStatus(StrEnum):
    """Overall transaction readiness status."""

    ready = "ready"
    conditional = "conditional"
    not_ready = "not_ready"


class InsuranceRiskTier(StrEnum):
    """Insurance premium risk tiers (tier_1 = lowest risk)."""

    tier_1 = "tier_1"
    tier_2 = "tier_2"
    tier_3 = "tier_3"
    tier_4 = "tier_4"


class TransactionCheck(BaseModel):
    """A single check in the transaction readiness evaluation."""

    check_id: str
    category: str
    label: str
    status: CheckStatus
    severity: CheckSeverity
    detail: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionReadiness(BaseModel):
    """Overall transaction readiness evaluation for a building."""

    building_id: UUID
    transaction_type: TransactionType
    overall_status: OverallStatus
    score: float
    checks: list[TransactionCheck]
    blockers: list[str]
    conditions: list[str]
    recommendations: list[str]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Insurance risk assessment
# ---------------------------------------------------------------------------


class InsuranceRiskAssessment(BaseModel):
    """Insurance premium risk tier assessment for a building."""

    building_id: UUID
    risk_tier: InsuranceRiskTier
    pollutant_diversity: int = Field(description="Number of distinct pollutant types found")
    threshold_exceedance_count: int = Field(description="Number of samples exceeding thresholds")
    intervention_coverage: float = Field(description="Fraction of hazards with completed interventions (0.0-1.0)")
    building_age_factor: float = Field(description="Age risk factor (1.0 = post-1990, 1.5 = pre-1990)")
    raw_score: float = Field(description="Weighted raw score before tier assignment")
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Financing score breakdown
# ---------------------------------------------------------------------------


class FinancingScoreBreakdown(BaseModel):
    """Detailed financing score with sub-scores for a building."""

    building_id: UUID
    documentation_score: float = Field(description="Score based on completeness + evidence count (0.0-1.0)")
    risk_mitigation_score: float = Field(description="Interventions completed / hazards found (0.0-1.0)")
    regulatory_compliance_score: float = Field(description="Completed diagnostics per pollutant coverage (0.0-1.0)")
    overall_score: float = Field(description="Weighted overall financing score (0.0-1.0)")
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Comparative readiness
# ---------------------------------------------------------------------------


class BuildingReadinessRank(BaseModel):
    """Readiness ranking for a single building within a comparison."""

    building_id: UUID
    transaction_type: TransactionType
    score: float
    overall_status: OverallStatus
    rank: int

    model_config = ConfigDict(from_attributes=True)


class ComparativeReadiness(BaseModel):
    """Comparative transaction readiness across multiple buildings."""

    transaction_type: TransactionType
    rankings: list[BuildingReadinessRank]

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Readiness trend
# ---------------------------------------------------------------------------


class ReadinessTrendPoint(BaseModel):
    """A single point in the readiness trend timeline."""

    month: str = Field(description="Month label (YYYY-MM)")
    score: float
    overall_status: OverallStatus

    model_config = ConfigDict(from_attributes=True)


class ReadinessTrend(BaseModel):
    """Readiness trend over time for a building and transaction type."""

    building_id: UUID
    transaction_type: TransactionType
    data_points: list[ReadinessTrendPoint]

    model_config = ConfigDict(from_attributes=True)
