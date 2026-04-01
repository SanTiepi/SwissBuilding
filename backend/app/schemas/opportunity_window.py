"""Pydantic v2 schemas for the OpportunityWindow detection service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from pydantic import BaseModel, computed_field


class OpportunityWindowResponse(BaseModel):
    """Single opportunity window with computed days_remaining."""

    id: UUID
    building_id: UUID
    case_id: UUID | None = None

    window_type: str
    title: str
    description: str | None = None

    window_start: date
    window_end: date
    optimal_date: date | None = None

    advantage: str | None = None
    expiry_risk: str = "low"
    cost_of_missing: str | None = None

    detected_by: str = "system"
    confidence: float | None = None
    status: str = "active"

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_remaining(self) -> int:
        """Days until window closes (0 if already past)."""
        today = datetime.now(UTC).date()
        delta = (self.window_end - today).days
        return max(delta, 0)


class WindowTypeSummary(BaseModel):
    """Count of windows per type."""

    window_type: str
    count: int


class OpportunityWindowListResponse(BaseModel):
    """List of opportunity windows with summary counts by type."""

    windows: list[OpportunityWindowResponse] = []
    total: int = 0
    by_type: list[WindowTypeSummary] = []


class OpportunityWindowDetectResponse(BaseModel):
    """Response after triggering window detection."""

    detected: int = 0
    new: int = 0
    windows: list[OpportunityWindowResponse] = []
    by_type: list[WindowTypeSummary] = []


class PortfolioWindowListResponse(BaseModel):
    """Portfolio-level opportunity windows across an organization."""

    organization_id: UUID
    windows: list[OpportunityWindowResponse] = []
    total: int = 0
    by_type: list[WindowTypeSummary] = []
    buildings_with_windows: int = 0
