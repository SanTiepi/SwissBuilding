"""Stable, versioned ERP-grade payload schemas.

These schemas form a CONTRACT with external ERP systems (Quorum, ImmoTop, etc.).
Version bumps only on breaking changes. Additive fields are non-breaking.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

ERP_PAYLOAD_VERSION = "1.0"


class ErpSafeToStart(BaseModel):
    """Go/no-go verdict consumable by an ERP."""

    status: str  # ready_to_proceed | proceed_with_conditions | diagnostic_required | critical_risk | memory_incomplete
    conditions: list[str] = Field(default_factory=list)
    confidence: str = "low"  # high | medium | low


class ErpBlocker(BaseModel):
    """A blocker preventing action on a building."""

    type: str  # procedure | obligation | unknown | contradiction
    title: str
    severity: str  # critical | high | medium
    reference_id: _uuid.UUID | None = None


class ErpNextAction(BaseModel):
    """Concrete next action an ERP should surface to users."""

    title: str
    priority: str  # urgent | recommended | optional
    category: str  # diagnostic | remediation | procedure | proof


class ErpProofStatus(BaseModel):
    """What is proven and what is missing."""

    diagnostic_coverage: float = 0.0  # 0-1
    authority_pack_ready: bool = False
    last_diagnostic_date: date | None = None
    pollutants_assessed: list[str] = Field(default_factory=list)
    pollutants_missing: list[str] = Field(default_factory=list)


class ErpObligation(BaseModel):
    """A deadline or recurring obligation the ERP should track."""

    title: str
    due_date: date | None = None
    status: str  # pending | overdue | completed
    category: str


# ---------------------------------------------------------------------------
# Building payload
# ---------------------------------------------------------------------------


class ErpBuildingPayload(BaseModel):
    """Stable ERP-grade payload for a single building.

    Version bumps only on breaking changes.
    """

    payload_version: str = ERP_PAYLOAD_VERSION
    generated_at: datetime

    building_id: _uuid.UUID

    # Identity (what ERP needs to match)
    egid: int | None = None
    egrid: str | None = None
    address: str | None = None
    npa: str | None = None
    city: str | None = None

    # Safe-to-start verdict
    safe_to_start: ErpSafeToStart = Field(default_factory=lambda: ErpSafeToStart(status="memory_incomplete"))

    # Blockers (what prevents action)
    blockers: list[ErpBlocker] = Field(default_factory=list)

    # Next actions (what ERP should surface to users)
    next_actions: list[ErpNextAction] = Field(default_factory=list)

    # Proof status (what's proven, what's missing)
    proof_status: ErpProofStatus = Field(default_factory=ErpProofStatus)

    # Obligations (deadlines ERP should track)
    obligations: list[ErpObligation] = Field(default_factory=list)

    # Grade summary
    passport_grade: str | None = None  # A-F
    trust_score: float | None = None  # 0-1
    completeness: float | None = None  # 0-1


# ---------------------------------------------------------------------------
# Portfolio payload
# ---------------------------------------------------------------------------


class ErpPortfolioPayload(BaseModel):
    """Stable ERP-grade payload for an organization's building portfolio."""

    payload_version: str = ERP_PAYLOAD_VERSION
    generated_at: datetime
    org_id: _uuid.UUID
    building_count: int = 0
    critical_count: int = 0
    action_needed_count: int = 0
    buildings: list[ErpBuildingPayload] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Version info
# ---------------------------------------------------------------------------


class ErpVersionInfo(BaseModel):
    """Current payload version and changelog."""

    current_version: str = ERP_PAYLOAD_VERSION
    changelog: list[str] = Field(
        default_factory=lambda: [
            "1.0 — Initial stable release: identity, safe-to-start, blockers, next actions, proof status, obligations, grade summary.",
        ]
    )
