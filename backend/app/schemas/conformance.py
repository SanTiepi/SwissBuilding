"""BatiConnect — Conformance Check schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# RequirementProfile
# ---------------------------------------------------------------------------


class RequirementProfileCreate(BaseModel):
    name: str
    description: str | None = None
    profile_type: str  # pack | import | publication | exchange | procedure
    required_sections: list[str] | None = None
    required_fields: list[str] | None = None
    minimum_completeness: float | None = Field(None, ge=0.0, le=1.0)
    minimum_trust: float | None = Field(None, ge=0.0, le=1.0)
    required_readiness: dict[str, str] | None = None
    max_unknowns: int | None = Field(None, ge=0)
    max_contradictions: int | None = Field(None, ge=0)
    redaction_allowed: bool = True


class RequirementProfileRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    profile_type: str
    required_sections: list[str] | None
    required_fields: list[str] | None
    minimum_completeness: float | None
    minimum_trust: float | None
    required_readiness: dict[str, str] | None
    max_unknowns: int | None
    max_contradictions: int | None
    redaction_allowed: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ConformanceCheck
# ---------------------------------------------------------------------------


class ConformanceCheckRequest(BaseModel):
    """Request to run a conformance check."""

    profile_name: str  # name of the requirement profile to check against
    target_type: str  # pack | passport | import | publication
    target_id: UUID | None = None  # optional ID of a specific artifact


class CheckDetail(BaseModel):
    check: str
    status: str  # pass | fail | warning
    reason: str | None = None


class ConformanceCheckRead(BaseModel):
    id: UUID
    building_id: UUID
    profile_id: UUID
    checked_by_id: UUID | None
    target_type: str
    target_id: UUID | None
    result: str  # pass | fail | partial
    score: float
    checks_passed: list[dict] | None
    checks_failed: list[dict] | None
    checks_warning: list[dict] | None
    summary: str | None
    checked_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConformanceCheckSummary(BaseModel):
    """Lightweight summary of conformance state for a building."""

    building_id: UUID
    total_checks: int
    passed: int
    failed: int
    partial: int
    latest_check: ConformanceCheckRead | None
