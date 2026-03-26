"""Schemas for portfolio triage (read model)."""

from __future__ import annotations

import uuid as _uuid

from pydantic import BaseModel, Field


class PortfolioTriageBuilding(BaseModel):
    id: _uuid.UUID
    address: str
    status: str  # critical | action_needed | monitored | under_control
    top_blocker: str | None = None
    risk_score: float = 0.0
    next_action: str | None = None
    passport_grade: str = "F"


class PortfolioTriageResult(BaseModel):
    org_id: _uuid.UUID
    critical_count: int = 0
    action_needed_count: int = 0
    monitored_count: int = 0
    under_control_count: int = 0
    buildings: list[PortfolioTriageBuilding] = Field(default_factory=list)
