"""Pydantic v2 schemas for the Recommendation Engine."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostEstimate(BaseModel):
    """Estimated cost range for a recommendation."""

    min: int = Field(..., ge=0)
    max: int = Field(..., ge=0)
    currency: str = "CHF"
    confidence: str = "estimated"  # estimated, market_data, fixed

    model_config = ConfigDict(from_attributes=True)


class RelatedEntity(BaseModel):
    """Reference to the entity that triggered the recommendation."""

    entity_type: str
    entity_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationRead(BaseModel):
    """A single prioritized recommendation."""

    id: str
    priority: int = Field(..., ge=1, le=4)  # 1=critical, 2=high, 3=medium, 4=low
    category: str  # remediation, investigation, documentation, compliance, monitoring
    title: str
    description: str
    why: str
    impact_score: float = Field(..., ge=0.0, le=1.0)
    cost_estimate: CostEstimate | None = None
    urgency_days: int | None = None
    source: str  # action_generator, readiness_reasoner, unknown_generator, trust_score
    related_entity: RelatedEntity | None = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationListRead(BaseModel):
    """List of recommendations for a building."""

    building_id: UUID
    recommendations: list[RecommendationRead]
    total: int

    model_config = ConfigDict(from_attributes=True)
