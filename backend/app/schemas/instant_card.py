"""Schemas for the instant card (decision-grade building intelligence)."""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# What We Know
# ---------------------------------------------------------------------------


class ResidualMaterial(BaseModel):
    material_type: str
    location: str | None = None
    status: str = "present"  # present | removed | encapsulated
    last_verified: str | None = None
    source: str | None = None


class WhatWeKnow(BaseModel):
    identity: dict[str, Any] = Field(default_factory=dict)
    physical: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    energy: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    residual_materials: list[ResidualMaterial] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# What Is Risky
# ---------------------------------------------------------------------------


class WhatIsRisky(BaseModel):
    pollutant_risk: dict[str, Any] = Field(default_factory=dict)
    environmental_risk: dict[str, Any] = Field(default_factory=dict)
    compliance_gaps: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# What Blocks
# ---------------------------------------------------------------------------


class WhatBlocks(BaseModel):
    procedural_blockers: list[dict[str, Any]] = Field(default_factory=list)
    missing_proof: list[dict[str, Any]] = Field(default_factory=list)
    overdue_obligations: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# What To Do Next
# ---------------------------------------------------------------------------


class NextAction(BaseModel):
    action: str
    priority: str = "medium"
    estimated_cost: float | None = None
    evidence_needed: str | None = None


class WhatToDoNext(BaseModel):
    top_3_actions: list[NextAction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# What Is Reusable
# ---------------------------------------------------------------------------


class WhatIsReusable(BaseModel):
    diagnostic_publications: list[dict[str, Any]] = Field(default_factory=list)
    packs_generated: list[dict[str, Any]] = Field(default_factory=list)
    proof_deliveries: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Execution section (Lot C)
# ---------------------------------------------------------------------------


class RenovationPlanItem(BaseModel):
    component: str
    action: str
    cost_chf: float = 0.0
    subsidy_chf: float = 0.0


class SubsidyRef(BaseModel):
    program: str
    amount: float = 0.0
    requirements: list[str] = Field(default_factory=list)


class ExecutionSection(BaseModel):
    renovation_plan_10y: dict[str, Any] = Field(default_factory=dict)
    subsidies: list[SubsidyRef] = Field(default_factory=list)
    roi_renovation: dict[str, Any] = Field(default_factory=dict)
    insurance_impact: dict[str, Any] = Field(default_factory=dict)
    co2_impact: dict[str, Any] = Field(default_factory=dict)
    energy_savings: dict[str, Any] = Field(default_factory=dict)
    sequence_recommendation: dict[str, Any] = Field(default_factory=dict)
    next_concrete_step: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trust metadata
# ---------------------------------------------------------------------------


class TrustMeta(BaseModel):
    freshness: str = "unknown"
    confidence: str = "medium"
    overall_trust: float = 0.0
    trend: str | None = None


# ---------------------------------------------------------------------------
# Evidence by nature (source_class grouping)
# ---------------------------------------------------------------------------


class EvidenceByNature(BaseModel):
    """Evidence grouped by source_class taxonomy."""

    official_truth: dict[str, Any] = Field(default_factory=dict)
    documentary_proof: dict[str, Any] = Field(default_factory=dict)
    observations: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)
    inferences: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Main InstantCard
# ---------------------------------------------------------------------------


class InstantCardResult(BaseModel):
    """Full decision-grade instant card for an existing building."""

    building_id: _uuid.UUID
    passport_grade: str = "F"
    what_we_know: WhatWeKnow = Field(default_factory=WhatWeKnow)
    evidence_by_nature: EvidenceByNature = Field(default_factory=EvidenceByNature)
    safe_to_start: dict[str, Any] = Field(default_factory=dict)
    what_is_risky: WhatIsRisky = Field(default_factory=WhatIsRisky)
    what_blocks: WhatBlocks = Field(default_factory=WhatBlocks)
    what_to_do_next: WhatToDoNext = Field(default_factory=WhatToDoNext)
    what_is_reusable: WhatIsReusable = Field(default_factory=WhatIsReusable)
    execution: ExecutionSection = Field(default_factory=ExecutionSection)
    trust: TrustMeta = Field(default_factory=TrustMeta)
    neighbor_signals: list[dict[str, Any]] = Field(default_factory=list)
