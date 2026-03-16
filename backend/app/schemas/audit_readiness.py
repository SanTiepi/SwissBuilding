"""Pydantic v2 schemas for the Audit Readiness service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Shared sub-schemas
# ---------------------------------------------------------------------------


class AuditReadinessCheck(BaseModel):
    """A single weighted check in the audit readiness evaluation."""

    id: str
    category: str  # documentation, compliance, evidence, process
    label: str
    status: str  # done, missing, partial
    weight: float
    detail: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditChecklistItem(BaseModel):
    """One actionable item in the audit checklist."""

    id: str
    category: str  # documentation, compliance, evidence, process
    label: str
    required: bool
    status: str  # done, missing, partial
    fix_action: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditFlag(BaseModel):
    """A concern that would be raised during an authority audit."""

    id: str
    severity: str  # critical, major, minor
    description: str
    recommendation: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AuditReadinessResult(BaseModel):
    """FN1 - Overall audit readiness evaluation for a building."""

    building_id: UUID
    score: int  # 0-100
    checks: list[AuditReadinessCheck]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditChecklist(BaseModel):
    """FN2 - Actionable checklist grouped by category."""

    building_id: UUID
    items: list[AuditChecklistItem]
    total_items: int
    done_count: int
    missing_count: int
    partial_count: int
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditSimulationResult(BaseModel):
    """FN3 - Predicted audit outcome."""

    building_id: UUID
    outcome: str  # pass, conditional, fail
    flags: list[AuditFlag]
    recommendations: list[str]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingAuditSummary(BaseModel):
    """Per-building summary inside the portfolio response."""

    building_id: UUID
    address: str
    score: int
    ready: bool
    estimated_prep_hours: float

    model_config = ConfigDict(from_attributes=True)


class PortfolioAuditReadiness(BaseModel):
    """FN4 - Organisation-level audit readiness overview."""

    organization_id: UUID
    average_score: float
    buildings_ready: int
    buildings_needing_prep: int
    total_buildings: int
    buildings: list[BuildingAuditSummary]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
