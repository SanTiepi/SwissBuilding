"""Schemas for reporting metrics: KPI dashboard, operational metrics, periodic reports, benchmarks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class TrendValue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current: float = 0.0
    previous: float = 0.0
    change_pct: float = 0.0
    direction: str = "stable"  # up | down | stable


# ---------------------------------------------------------------------------
# FN1 — KPI Dashboard
# ---------------------------------------------------------------------------


class KPIDashboard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    buildings_assessed_pct: TrendValue
    compliance_rate_pct: TrendValue
    avg_risk_score: TrendValue
    avg_quality_score: TrendValue
    remediation_progress_pct: TrendValue
    active_interventions_count: TrendValue
    total_estimated_chf: float = 0.0
    total_spent_chf: float = 0.0
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN2 — Operational Metrics
# ---------------------------------------------------------------------------


class OperationalMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    avg_diagnostic_completion_days: float = 0.0
    avg_diagnostic_to_remediation_days: float = 0.0
    sample_throughput_per_month: float = 0.0
    document_upload_rate_per_month: float = 0.0
    action_completion_rate_pct: float = 0.0
    total_diagnostics: int = 0
    total_samples: int = 0
    total_documents: int = 0
    total_actions: int = 0
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN3 — Periodic Report
# ---------------------------------------------------------------------------


class PeriodicReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    period: str  # monthly | quarterly | annual
    period_start: datetime
    period_end: datetime
    summary: str = ""
    buildings_count: int = 0
    new_diagnostics: int = 0
    completed_diagnostics: int = 0
    new_risks_identified: int = 0
    high_risk_buildings: int = 0
    remediation_progress_pct: float = 0.0
    interventions_completed: int = 0
    interventions_in_progress: int = 0
    compliance_improvements: int = 0
    budget_estimated_chf: float = 0.0
    budget_spent_chf: float = 0.0
    budget_utilization_pct: float = 0.0
    key_changes: list[str] = Field(default_factory=list)
    generated_at: datetime


# ---------------------------------------------------------------------------
# FN4 — Benchmark Comparison
# ---------------------------------------------------------------------------


class BenchmarkMetric(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_name: str
    org_value: float = 0.0
    system_avg: float = 0.0
    difference: float = 0.0
    percentile: float = 0.0
    is_above_avg: bool = False


class BenchmarkComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    compliance_rate: BenchmarkMetric
    avg_risk_score: BenchmarkMetric
    avg_quality_score: BenchmarkMetric
    avg_diagnostic_speed_days: BenchmarkMetric
    action_completion_rate: BenchmarkMetric
    overall_percentile: float = 0.0
    generated_at: datetime
