"""
BatiConnect — Indispensability Schemas

Pydantic v2 schemas for fragmentation, defensibility, counterfactual,
and combined indispensability reports.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Fragmentation sub-schemas
# ---------------------------------------------------------------------------


class SourceDispersion(BaseModel):
    sources_unified: int
    systems_replaced: list[str]


class ContradictionValue(BaseModel):
    contradictions_detected: int
    contradictions_resolved: int
    silent_risk: str


class ProofChainIntegrity(BaseModel):
    proof_chains_count: int
    documents_with_provenance: int
    documents_without_provenance: int


class KnowledgeConsolidation(BaseModel):
    enrichment_fields_count: int
    manual_fields_count: int
    cross_source_fields: int


class FragmentationResult(BaseModel):
    building_id: UUID
    source_dispersion: SourceDispersion
    contradiction_value: ContradictionValue
    proof_chain_integrity: ProofChainIntegrity
    knowledge_consolidation: KnowledgeConsolidation
    fragmentation_score: float


# ---------------------------------------------------------------------------
# Defensibility sub-schemas
# ---------------------------------------------------------------------------


class DecisionAuditTrail(BaseModel):
    actions_with_evidence: int
    obligations_tracked: int
    procedures_traced: int
    packs_with_hash: int


class EvidenceDepth(BaseModel):
    safe_to_start_sources: int
    risk_assessment_data_points: int
    compliance_artefacts: int


class WithoutUsScenario(BaseModel):
    decisions_with_full_trace: int
    decisions_without_trace: int
    defensibility_score: float
    vulnerability_points: list[str]


class TemporalDefensibility(BaseModel):
    snapshots_count: int
    time_coverage_days: int
    temporal_gaps: list[str]


class DefensibilityResult(BaseModel):
    building_id: UUID
    decision_audit_trail: DecisionAuditTrail
    evidence_depth: EvidenceDepth
    without_us_scenario: WithoutUsScenario
    temporal_defensibility: TemporalDefensibility


# ---------------------------------------------------------------------------
# Counterfactual sub-schemas
# ---------------------------------------------------------------------------


class PlatformState(BaseModel):
    sources_unified: int
    contradictions_resolved: int
    proof_chains: int
    passport_grade: str
    overall_trust: float
    completeness: float


class FragmentationCost(BaseModel):
    hours_to_reconstruct: float
    cost_chf: float
    breakdown: dict[str, float]


class CounterfactualResult(BaseModel):
    building_id: UUID
    with_platform: PlatformState
    without_platform: PlatformState
    delta: list[str]
    cost_of_fragmentation: FragmentationCost


# ---------------------------------------------------------------------------
# Combined report
# ---------------------------------------------------------------------------


class IndispensabilityReport(BaseModel):
    building_id: UUID
    generated_at: datetime
    fragmentation: FragmentationResult
    defensibility: DefensibilityResult
    counterfactual: CounterfactualResult
    headline: str


# ---------------------------------------------------------------------------
# Portfolio-level summary
# ---------------------------------------------------------------------------


class BuildingIndispensabilitySummary(BaseModel):
    building_id: UUID
    address: str
    fragmentation_score: float
    defensibility_score: float


class PortfolioIndispensabilitySummary(BaseModel):
    organization_id: UUID
    buildings_count: int
    avg_fragmentation_score: float
    avg_defensibility_score: float
    worst_fragmentation: list[BuildingIndispensabilitySummary]
    worst_defensibility: list[BuildingIndispensabilitySummary]
