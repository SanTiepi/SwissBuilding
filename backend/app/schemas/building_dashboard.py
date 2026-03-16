"""Pydantic v2 schemas for the Building Dashboard aggregate read model."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DashboardTrustSummary(BaseModel):
    """Trust score summary for dashboard."""

    score: float | None = None
    level: str | None = None  # high | medium | low
    trend: str | None = None  # improving | stable | declining

    model_config = ConfigDict(from_attributes=True)


class DashboardReadinessSummary(BaseModel):
    """Readiness summary for dashboard."""

    overall_status: str | None = None  # ready | partially_ready | not_ready | unknown
    blocked_count: int = 0
    gate_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DashboardCompletenessSummary(BaseModel):
    """Completeness summary for dashboard."""

    overall_score: float | None = None
    category_scores: dict[str, float] | None = None
    missing_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DashboardRiskSummary(BaseModel):
    """Risk summary for dashboard."""

    risk_level: str | None = None
    risk_score: float | None = None
    pollutant_risks: dict[str, str] | None = None

    model_config = ConfigDict(from_attributes=True)


class DashboardComplianceSummary(BaseModel):
    """Compliance summary for dashboard."""

    status: str | None = None  # compliant | non_compliant | partially_compliant | unknown
    overdue_count: int = 0
    upcoming_deadlines: int = 0
    gap_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DashboardActivitySummary(BaseModel):
    """Activity counts for dashboard."""

    total_diagnostics: int = 0
    completed_diagnostics: int = 0
    total_interventions: int = 0
    active_interventions: int = 0
    open_actions: int = 0
    total_documents: int = 0
    total_zones: int = 0
    total_samples: int = 0

    model_config = ConfigDict(from_attributes=True)


class DashboardAlertsSummary(BaseModel):
    """Alerts and issues summary for dashboard."""

    weak_signals: int = 0
    constraint_blockers: int = 0
    quality_issues: int = 0
    open_unknowns: int = 0

    model_config = ConfigDict(from_attributes=True)


class BuildingDashboard(BaseModel):
    """Complete dashboard aggregate for a single building."""

    building_id: UUID
    address: str
    city: str
    canton: str
    passport_grade: str | None = None
    trust: DashboardTrustSummary
    readiness: DashboardReadinessSummary
    completeness: DashboardCompletenessSummary
    risk: DashboardRiskSummary
    compliance: DashboardComplianceSummary
    activity: DashboardActivitySummary
    alerts: DashboardAlertsSummary
    last_updated: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
