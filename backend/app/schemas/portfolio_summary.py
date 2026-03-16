from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PortfolioOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_buildings: int = 0
    total_diagnostics: int = 0
    total_interventions: int = 0
    total_documents: int = 0
    active_campaigns: int = 0
    avg_completeness: float | None = None
    avg_trust: float | None = None


class PortfolioRiskDistribution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    by_level: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0, "unknown": 0}
    avg_risk_score: float | None = None
    buildings_above_threshold: int = 0


class PortfolioComplianceOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    compliant_count: int = 0
    non_compliant_count: int = 0
    partially_compliant_count: int = 0
    unknown_count: int = 0
    total_overdue_deadlines: int = 0


class PortfolioReadinessOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ready_count: int = 0
    partially_ready_count: int = 0
    not_ready_count: int = 0
    unknown_count: int = 0


class PortfolioGradeDistribution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    by_grade: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "None": 0}


class PortfolioActionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_open: int = 0
    total_in_progress: int = 0
    total_completed: int = 0
    by_priority: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    overdue_count: int = 0


class PortfolioAlertSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_weak_signals: int = 0
    buildings_on_critical_path: int = 0
    total_constraint_blockers: int = 0
    buildings_with_stale_diagnostics: int = 0


class PortfolioSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overview: PortfolioOverview
    risk: PortfolioRiskDistribution
    compliance: PortfolioComplianceOverview
    readiness: PortfolioReadinessOverview
    grades: PortfolioGradeDistribution
    actions: PortfolioActionSummary
    alerts: PortfolioAlertSummary
    generated_at: datetime
    organization_id: UUID | None = None


class PortfolioCompareRequest(BaseModel):
    organization_ids: list[UUID]
