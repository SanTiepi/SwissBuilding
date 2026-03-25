"""BatiConnect — Intelligence Stack schemas (AI extraction, patterns, advisor, narrative, comparison, benchmark)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Certificate extraction
# ---------------------------------------------------------------------------


class CertificateExtractionDraft(BaseModel):
    certificate_type: str | None = None
    issuer: str | None = None
    date_issued: str | None = None
    building_ref: str | None = None
    pollutant: str | None = None
    result: str | None = None
    confidence_per_field: dict[str, float] = {}
    ambiguous_fields: list[dict] = []
    unknown_fields: list[dict] = []


# ---------------------------------------------------------------------------
# AI Rule Pattern
# ---------------------------------------------------------------------------


class AIRulePatternRead(BaseModel):
    id: UUID
    pattern_type: str
    source_entity_type: str
    rule_key: str
    rule_definition: dict | None = None
    sample_count: int
    last_confirmed_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIPatternStats(BaseModel):
    total_patterns: int
    by_type: dict[str, int]
    avg_sample_count: float


# ---------------------------------------------------------------------------
# Readiness Advisor
# ---------------------------------------------------------------------------


class ReadinessAdvisorSuggestion(BaseModel):
    type: str  # blocker | gap | stale | missing_pollutant | pending_procedure | proof_gap
    title: str
    description: str
    evidence_refs: list[str] = []
    confidence: float = 0.0
    recommended_action: str | None = None


class ReadinessAdvisorResponse(BaseModel):
    building_id: UUID
    suggestions: list[ReadinessAdvisorSuggestion]
    generated_at: datetime


# ---------------------------------------------------------------------------
# Passport Narrative
# ---------------------------------------------------------------------------


class NarrativeSection(BaseModel):
    title: str
    body: str
    evidence_refs: list[str] = []
    caveats: list[str] = []
    audience_specific: bool = False


class PassportNarrativeResponse(BaseModel):
    building_id: UUID
    audience: str
    sections: list[NarrativeSection]
    generated_at: datetime


# ---------------------------------------------------------------------------
# Quote Comparison Intelligence
# ---------------------------------------------------------------------------


class ScopeCoverageItem(BaseModel):
    item: str
    present_in: list[str]  # company names
    missing_from: list[str]


class QuoteComparisonInsight(BaseModel):
    request_id: UUID
    scope_coverage_matrix: list[ScopeCoverageItem]
    price_spread: dict  # {min, max, median, range_pct}
    timeline_spread: dict  # {min_weeks, max_weeks, median_weeks}
    common_exclusions: list[str]
    ambiguity_flags: list[dict]  # [{field, quotes_affected, description}]
    quote_count: int


# ---------------------------------------------------------------------------
# Remediation Benchmark
# ---------------------------------------------------------------------------


class PollutantBenchmark(BaseModel):
    pollutant: str
    avg_cost_chf: float
    avg_cycle_days: float
    completion_rate: float
    sample_size: int


class RemediationBenchmarkSnapshot(BaseModel):
    org_id: UUID
    benchmarks: list[PollutantBenchmark]
    overall_avg_cost_chf: float
    overall_avg_cycle_days: float
    overall_completion_rate: float
    generated_at: datetime


# ---------------------------------------------------------------------------
# Flywheel Trends
# ---------------------------------------------------------------------------


class FlywheelTrendPoint(BaseModel):
    date: str  # ISO date
    extraction_quality: float
    correction_rate: float
    cycle_time_days: float | None = None
    knowledge_density: float


class KnowledgeDensityTrend(BaseModel):
    org_id: UUID
    density: float
    completed_cycles: int
    total_buildings: int


# ---------------------------------------------------------------------------
# Module Learning Overview (admin)
# ---------------------------------------------------------------------------


class ModuleLearningOverview(BaseModel):
    total_patterns: int
    extraction_success_rate: float
    avg_confidence: float
    top_correction_categories: list[dict]  # [{category, count}]
    total_extractions: int
    total_feedbacks: int
