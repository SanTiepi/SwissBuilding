"""BatiConnect - Operational Gate schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Prerequisite detail
# ---------------------------------------------------------------------------


class GatePrerequisite(BaseModel):
    """Individual prerequisite with satisfied/unsatisfied status."""

    type: str = Field(
        ...,
        description="engagement | document | proof_chain | diagnostic | obligation | procedure | pack | safe_to_start",
    )
    subject_type: str | None = None
    engagement_type: str | None = None
    label: str
    satisfied: bool = False
    item_id: UUID | None = None


# ---------------------------------------------------------------------------
# Read / List
# ---------------------------------------------------------------------------


class OperationalGateRead(BaseModel):
    """Full gate with prerequisites status."""

    id: UUID
    building_id: UUID
    gate_type: str
    gate_label: str
    status: str
    prerequisites: list[GatePrerequisite]
    overridden_by_id: UUID | None = None
    override_reason: str | None = None
    overridden_at: datetime | None = None
    cleared_at: datetime | None = None
    cleared_by_id: UUID | None = None
    auto_evaluate: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class OperationalGateList(BaseModel):
    """List of gates for a building."""

    building_id: UUID
    gates: list[OperationalGateRead]
    total: int


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------


class GateEvaluation(BaseModel):
    """Result of evaluating all gates for a building."""

    building_id: UUID
    gates: list[OperationalGateRead]
    total: int
    blocked: int
    conditions_pending: int
    clearable: int
    cleared: int
    overridden: int
    all_clear: bool


# ---------------------------------------------------------------------------
# Override request
# ---------------------------------------------------------------------------


class GateOverrideRequest(BaseModel):
    """Override a gate with reason."""

    reason: str = Field(..., min_length=10, description="Justification for the override (min 10 chars)")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class BuildingGateStatus(BaseModel):
    """Summary: total gates, blocked, clearable, cleared."""

    building_id: UUID
    total: int
    blocked: int
    conditions_pending: int
    clearable: int
    cleared: int
    overridden: int
    expired: int
    all_clear: bool
