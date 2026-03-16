"""Pydantic v2 schemas for the Priority Matrix."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Shared enums as literals
# ---------------------------------------------------------------------------

URGENCY_LEVELS = ("immediate", "short_term", "medium_term", "long_term")
IMPACT_LEVELS = ("critical", "high", "medium", "low")


# ---------------------------------------------------------------------------
# Matrix item schemas
# ---------------------------------------------------------------------------


class MatrixItem(BaseModel):
    """A single action or intervention placed in the matrix."""

    id: UUID
    item_type: str  # "action" or "intervention"
    title: str
    description: str | None = None
    urgency: str
    impact: str
    priority: str | None = None  # from ActionItem.priority
    status: str | None = None
    due_date: str | None = None
    pollutant_type: str | None = None
    risk_level: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MatrixCell(BaseModel):
    """A single cell in the urgency x impact matrix."""

    urgency: str
    impact: str
    items: list[MatrixItem]
    count: int

    model_config = ConfigDict(from_attributes=True)


class PriorityMatrix(BaseModel):
    """Full 2D priority matrix for a building."""

    building_id: UUID
    cells: list[MatrixCell]
    total_items: int
    summary: dict[str, int]  # quadrant label -> count
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Critical path schemas
# ---------------------------------------------------------------------------


class CriticalPathItem(BaseModel):
    """An item that must happen first (urgent + critical quadrant)."""

    id: UUID
    item_type: str
    title: str
    description: str | None = None
    blocking_reason: str
    dependencies: list[str]
    estimated_days: int
    priority: str | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CriticalPath(BaseModel):
    """Critical path: items in the urgent+critical quadrant."""

    building_id: UUID
    items: list[CriticalPathItem]
    total_blocking: int
    estimated_total_days: int
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Quick wins schemas
# ---------------------------------------------------------------------------


class QuickWinItem(BaseModel):
    """A low-effort, high-impact item."""

    id: UUID
    item_type: str
    title: str
    description: str | None = None
    effort_days: int
    risk_reduction: str  # qualitative: significant, moderate, minor
    cost_benefit: str  # qualitative assessment
    dependencies: list[str]

    model_config = ConfigDict(from_attributes=True)


class QuickWins(BaseModel):
    """Quick wins: low-effort, high-impact items."""

    building_id: UUID
    items: list[QuickWinItem]
    total_quick_wins: int
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Portfolio priority overview schemas
# ---------------------------------------------------------------------------


class BuildingPrioritySummary(BaseModel):
    """Priority summary for a single building in the portfolio."""

    building_id: UUID
    address: str
    city: str
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


class PortfolioPriorityOverview(BaseModel):
    """Org-level priority matrix aggregation."""

    organization_id: UUID
    building_count: int
    quadrant_totals: dict[str, int]  # "immediate_critical" -> count, etc.
    buildings_most_critical: list[BuildingPrioritySummary]
    resource_allocation: list[str]  # recommendations
    total_items: int
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
