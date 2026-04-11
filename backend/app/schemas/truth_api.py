"""Truth API v1 — Versioned response schemas for external read-side projections.

Every schema includes api_version, generated_at, and _links for HATEOAS-style navigation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Base envelope
# ---------------------------------------------------------------------------


class TruthEnvelopeV1(BaseModel):
    """Common envelope fields for all Truth API responses."""

    api_version: str = "1.0"
    generated_at: datetime
    links: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Building Summary
# ---------------------------------------------------------------------------


class BuildingSummaryIdentityV1(BaseModel):
    building_id: str
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    egid: int | None = None


class BuildingSummaryGradeV1(BaseModel):
    passport_grade: str
    overall_trust: float
    overall_completeness: float


class BuildingSummaryReadinessV1(BaseModel):
    safe_to_start: dict[str, Any] = Field(default_factory=dict)
    safe_to_tender: dict[str, Any] = Field(default_factory=dict)
    safe_to_reopen: dict[str, Any] = Field(default_factory=dict)
    safe_to_requalify: dict[str, Any] = Field(default_factory=dict)


class BuildingSummaryPollutantsV1(BaseModel):
    total_pollutants: int
    covered_count: int
    missing_count: int
    covered: dict[str, int] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)
    coverage_ratio: float


class BuildingSummaryDiagnosticsV1(BaseModel):
    diagnostics_count: int
    samples_count: int
    latest_diagnostic_date: str | None = None


class BuildingSummaryV1(TruthEnvelopeV1):
    """Versioned building summary with optional section filtering."""

    building_id: str
    sections_included: list[str] = Field(default_factory=list)
    identity: BuildingSummaryIdentityV1 | None = None
    spatial: dict[str, Any] | None = None
    grade: BuildingSummaryGradeV1 | None = None
    completeness: dict[str, Any] | None = None
    readiness: BuildingSummaryReadinessV1 | None = None
    trust: dict[str, Any] | None = None
    pollutants: BuildingSummaryPollutantsV1 | None = None
    diagnostics_summary: BuildingSummaryDiagnosticsV1 | None = None


# ---------------------------------------------------------------------------
# Identity Chain
# ---------------------------------------------------------------------------


class IdentityChainV1(TruthEnvelopeV1):
    """Auditable identity chain: EGID, EGRID, RDPPF, parcel."""

    building_id: str
    egid: dict[str, Any] = Field(default_factory=dict)
    egrid: dict[str, Any] = Field(default_factory=dict)
    rdppf: dict[str, Any] = Field(default_factory=dict)
    chain_complete: bool = False
    chain_gaps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SafeToX
# ---------------------------------------------------------------------------


class SafeToXVerdictV1(BaseModel):
    safe_to_type: str
    verdict: str
    verdict_summary: str
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    evaluated_at: str | None = None
    rule_basis: list[str] = Field(default_factory=list)


class SafeToXSummaryV1(TruthEnvelopeV1):
    """SafeToX verdicts: start, sell, insure, finance, lease, transfer, tender."""

    building_id: str
    verdicts: list[SafeToXVerdictV1] = Field(default_factory=list)
    types_included: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Unknowns
# ---------------------------------------------------------------------------


class UnknownEntryV1(BaseModel):
    unknown_type: str
    status: str
    blocks_readiness: bool = False
    description: str | None = None
    severity: str | None = None


class UnknownsV1(TruthEnvelopeV1):
    """Unknowns ledger: what is missing, stale, unverified, contradicted."""

    building_id: str
    total_open: int = 0
    blocking: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    entries: list[UnknownEntryV1] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Change Timeline
# ---------------------------------------------------------------------------


class ChangeEntryV1(BaseModel):
    change_type: str
    timestamp: str | None = None
    description: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChangeTimelineV1(TruthEnvelopeV1):
    """Change timeline: observations, events, deltas, signals since a date."""

    building_id: str
    since: str | None = None
    total_changes: int = 0
    entries: list[ChangeEntryV1] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Passport
# ---------------------------------------------------------------------------


class PassportV1(TruthEnvelopeV1):
    """Latest sovereign passport envelope with optional redaction."""

    building_id: str
    redaction_profile: str = "none"
    passport_grade: str = "F"
    knowledge_state: dict[str, Any] = Field(default_factory=dict)
    completeness: dict[str, Any] = Field(default_factory=dict)
    readiness: dict[str, Any] = Field(default_factory=dict)
    blind_spots: dict[str, Any] = Field(default_factory=dict)
    contradictions: dict[str, Any] = Field(default_factory=dict)
    evidence_coverage: dict[str, Any] = Field(default_factory=dict)
    pollutant_coverage: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pack
# ---------------------------------------------------------------------------


class PackV1(TruthEnvelopeV1):
    """Audience-specific pack: authority, owner, insurer, contractor, notary, transfer."""

    building_id: str
    pack_type: str
    redaction_profile: str = "none"
    pack_version: str | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    integrity_hash: str | None = None
    completeness_score: float | None = None


# ---------------------------------------------------------------------------
# Portfolio Overview
# ---------------------------------------------------------------------------


class PortfolioBuildingRowV1(BaseModel):
    building_id: str
    building_name: str
    passport_grade: str
    completeness_pct: float
    trust_pct: float
    readiness_status: str
    open_actions_count: int = 0
    risk_level: str = "unknown"


class PortfolioOverviewV1(TruthEnvelopeV1):
    """Portfolio-level overview: grades, readiness, priorities, budget horizon."""

    org_id: str | None = None
    total_buildings: int = 0
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    readiness_distribution: dict[str, int] = Field(default_factory=dict)
    avg_completeness: float = 0.0
    avg_trust: float = 0.0
    top_priorities: list[dict[str, Any]] = Field(default_factory=list)
    budget_horizon: dict[str, Any] = Field(default_factory=dict)
    buildings: list[PortfolioBuildingRowV1] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class AlertV1(BaseModel):
    alert_type: str
    severity: str
    building_id: str | None = None
    building_name: str | None = None
    title: str
    description: str | None = None
    deadline: str | None = None
    days_remaining: int | None = None


class AlertsV1(TruthEnvelopeV1):
    """Predictive alerts across portfolio."""

    org_id: str | None = None
    total_alerts: int = 0
    alerts: list[AlertV1] = Field(default_factory=list)
