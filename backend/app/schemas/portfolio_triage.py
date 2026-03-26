"""Schemas for portfolio triage (read model)."""

from __future__ import annotations

import uuid as _uuid

from pydantic import BaseModel, Field


class PortfolioTriageBuilding(BaseModel):
    id: _uuid.UUID
    address: str
    status: str  # critical | action_needed | monitored | under_control
    top_blocker: str | None = None
    risk_score: float = 0.0
    next_action: str | None = None
    passport_grade: str = "F"


class PortfolioTriageResult(BaseModel):
    org_id: _uuid.UUID
    critical_count: int = 0
    action_needed_count: int = 0
    monitored_count: int = 0
    under_control_count: int = 0
    buildings: list[PortfolioTriageBuilding] = Field(default_factory=list)


# ── Portfolio Benchmark schemas ──────────────────────────────────────


class BuildingBenchmark(BaseModel):
    """Per-building percentile ranks within the portfolio."""

    id: _uuid.UUID
    address: str
    passport_grade: str = "F"
    trust_score: float = 0.0
    completeness: float = 0.0
    risk_score: float = 0.0
    grade_percentile: float = 0.0  # 0-100, higher = better relative position
    trust_percentile: float = 0.0
    completeness_percentile: float = 0.0
    risk_percentile: float = 0.0  # 0-100, higher = lower risk (better)
    urgency_score: float = 0.0  # composite urgency (higher = more urgent)


class PortfolioKPI(BaseModel):
    """Portfolio-level aggregated KPIs."""

    avg_grade: str = "F"
    avg_trust: float = 0.0
    avg_completeness: float = 0.0
    buildings_with_blockers_pct: float = 0.0
    proof_coverage_pct: float = 0.0
    total_buildings: int = 0


class BuildingCluster(BaseModel):
    """Group of buildings with similar risk profile."""

    cluster_label: str  # e.g. "Grade-C / Trust-medium"
    grade: str
    trust_band: str  # low | medium | high
    building_ids: list[_uuid.UUID] = Field(default_factory=list)
    count: int = 0
    avg_risk_score: float = 0.0


class PortfolioPattern(BaseModel):
    """Recurring pattern detected across the portfolio."""

    pattern_type: str  # common_blocker | recurring_unknown | shared_proof_gap
    description: str
    affected_building_ids: list[_uuid.UUID] = Field(default_factory=list)
    frequency: int = 0


class PortfolioBenchmark(BaseModel):
    """Full portfolio benchmark result."""

    org_id: _uuid.UUID
    kpis: PortfolioKPI
    buildings: list[BuildingBenchmark] = Field(default_factory=list)
    worst_first: list[BuildingBenchmark] = Field(default_factory=list)
    clusters: list[BuildingCluster] = Field(default_factory=list)
    patterns: list[PortfolioPattern] = Field(default_factory=list)


# ── Portfolio Trends schemas ─────────────────────────────────────────


class BuildingTrend(BaseModel):
    """Trend for a single building based on snapshot comparison."""

    id: _uuid.UUID
    address: str
    direction: str  # improved | stable | degraded
    current_grade: str = "F"
    previous_grade: str | None = None
    current_trust: float = 0.0
    previous_trust: float | None = None
    snapshot_date: str | None = None  # ISO date of comparison snapshot


class PortfolioTrends(BaseModel):
    """Portfolio-level trend indicators."""

    org_id: _uuid.UUID
    overall_direction: str  # improved | stable | degraded
    improved_count: int = 0
    stable_count: int = 0
    degraded_count: int = 0
    buildings: list[BuildingTrend] = Field(default_factory=list)
