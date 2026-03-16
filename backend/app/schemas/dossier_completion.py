"""Pydantic v2 schemas for the Dossier Completion Agent."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompletionBlocker(BaseModel):
    """A blocker preventing dossier completion."""

    priority: str  # high, medium, low
    description: str
    source: str  # readiness, unknown
    readiness_type: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CompletionRecommendation(BaseModel):
    """A recommended action to improve dossier completeness."""

    priority: str  # high, medium, low
    description: str
    category: str  # evidence, diagnostic, document, regulatory, intervention
    entity_type: str | None = None
    entity_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class DossierCompletionReport(BaseModel):
    """Aggregated dossier completion analysis for a building."""

    building_id: UUID
    overall_status: str  # complete, near_complete, incomplete, critical_gaps
    completeness_score: float
    trust_score: float
    readiness_summary: dict[str, str]
    top_blockers: list[CompletionBlocker]
    recommended_actions: list[CompletionRecommendation]
    gap_categories: dict[str, int]
    data_quality_warnings: list[str]
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)
