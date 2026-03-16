"""Pydantic v2 schemas for the Sampling Planner."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SamplingRecommendation(BaseModel):
    """A single evidence-collection recommendation."""

    action_type: str  # sample_zone, sample_pollutant, confirm_material, upload_plan,
    # lab_analysis, document_intervention, refresh_diagnostic, visual_inspection
    priority: str  # critical, high, medium, low
    impact_score: float  # 0.0 - 1.0
    description: str
    entity_type: str  # zone, material, sample, building, diagnostic, intervention
    entity_id: UUID
    pollutant: str | None = None  # asbestos, pcb, lead, hap, radon
    rationale: str

    model_config = ConfigDict(from_attributes=True)


class SamplingPlan(BaseModel):
    """Full sampling plan for a building."""

    building_id: UUID
    total_recommendations: int
    recommendations: list[SamplingRecommendation]
    estimated_completeness_after: float
    priority_breakdown: dict[str, int]
    coverage_gaps: list[str]
    planned_at: datetime

    model_config = ConfigDict(from_attributes=True)
