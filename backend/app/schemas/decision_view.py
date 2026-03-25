"""Decision View — schemas for unified building decision surface."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DecisionBlocker(BaseModel):
    """A red-severity item blocking decision readiness."""

    id: str
    category: str  # procedure_blocked | overdue_obligation | missing_proof | unresolved_unknown
    title: str
    description: str
    source_type: str | None = None
    source_id: str | None = None
    link_hint: str | None = None  # frontend route hint


class DecisionCondition(BaseModel):
    """An orange-severity item requiring attention but not blocking."""

    id: str
    category: str  # review_required | aging_evidence | incomplete_coverage | stale_proof
    title: str
    description: str
    source_type: str | None = None
    source_id: str | None = None
    link_hint: str | None = None


class DecisionClearItem(BaseModel):
    """A green-severity item that is clear / resolved."""

    id: str
    category: str
    title: str
    description: str


class AudienceReadiness(BaseModel):
    """Readiness summary for one audience type."""

    audience: str  # authority | insurer | lender | transaction
    has_pack: bool = False
    latest_pack_version: int | None = None
    latest_pack_status: str | None = None
    latest_pack_generated_at: datetime | None = None
    included_sections: list[str] = []
    excluded_sections: list[str] = []
    unknowns_count: int = 0
    contradictions_count: int = 0
    residual_risks_count: int = 0
    caveats: list[str] = []
    trust_refs_count: int = 0
    proof_refs_count: int = 0


class ProofChainItem(BaseModel):
    """A single item in the proof chain summary."""

    label: str
    entity_type: str
    entity_id: str | None = None
    version: int | None = None
    content_hash: str | None = None
    status: str | None = None
    delivery_status: str | None = None
    occurred_at: datetime | None = None
    custody_chain_length: int = 0


class CustodyPosture(BaseModel):
    """Summary of artifact versioning and custody posture."""

    total_artifact_versions: int = 0
    current_versions: int = 0
    total_custody_events: int = 0
    latest_custody_event_at: datetime | None = None


class ROISummary(BaseModel):
    """Inline ROI summary from existing ROI calculator."""

    time_saved_hours: float = 0.0
    rework_avoided: int = 0
    blocker_days_saved: float = 0.0
    pack_reuse_count: int = 0
    evidence_sources: list[str] = []


class DecisionView(BaseModel):
    """The unified decision-grade view for a building."""

    building_id: UUID
    building_name: str
    building_address: str | None = None
    passport_grade: str = "F"
    overall_trust: float = 0.0
    overall_completeness: float = 0.0
    readiness_status: str = "not_evaluated"  # best readiness status across 4 types
    last_updated: datetime | None = None
    custody_posture: CustodyPosture = CustodyPosture()

    # Blockers & conditions
    blockers: list[DecisionBlocker] = []
    conditions: list[DecisionCondition] = []
    clear_items: list[DecisionClearItem] = []

    # Audience-specific readiness
    audience_readiness: list[AudienceReadiness] = []

    # Proof chain
    proof_chain: list[ProofChainItem] = []

    # ROI summary
    roi: ROISummary = ROISummary()
