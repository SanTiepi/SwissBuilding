"""Schemas for computed pilot scorecard metrics."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class PilotMetricResult(BaseModel):
    """A single computed pilot metric."""

    key: str
    label: str
    current_value: float
    target_value: float
    unit: str
    description: str


class PilotScorecardResult(BaseModel):
    """Aggregated pilot scorecard for an organization."""

    org_id: UUID
    pilot_score: float
    grade: str
    metrics: list[PilotMetricResult]
    computed_at: str
