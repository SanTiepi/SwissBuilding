"""Schemas for safe-to-start decision summary."""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from pydantic import BaseModel, Field


class SafeToStartAction(BaseModel):
    """A concrete next action with priority and responsible party."""

    action: str
    priority: str = "medium"  # critical | high | medium | low
    estimated_cost: float | None = None
    who: str | None = None


class SafeToStartResult(BaseModel):
    """Defensible go/no-go status for a building."""

    building_id: _uuid.UUID
    status: str  # ready_to_proceed | proceed_with_conditions | diagnostic_required | critical_risk | memory_incomplete
    blockers: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    next_actions: list[SafeToStartAction] = Field(default_factory=list)
    reusable_proof: list[str] = Field(default_factory=list)
    confidence: str = "low"  # high | medium | low
    explanation_fr: str = ""
    post_works_impact: dict[str, Any] = Field(default_factory=dict)
