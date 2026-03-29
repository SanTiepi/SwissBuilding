"""Pydantic v2 schemas for the Compliance Nudge Engine."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostOfInaction(BaseModel):
    """Estimated cost/risk of not acting."""

    description: str
    estimated_chf_min: int = Field(..., ge=0)
    estimated_chf_max: int = Field(..., ge=0)
    confidence: str = "estimated"  # estimated, market_data, regulatory

    model_config = ConfigDict(from_attributes=True)


class NudgeRelatedEntity(BaseModel):
    """Reference to the entity that triggered the nudge."""

    entity_type: str
    entity_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class NudgeRead(BaseModel):
    """A single behavioral nudge."""

    id: str
    nudge_type: str  # expiring_diagnostic, unaddressed_asbestos, etc.
    severity: str  # critical, warning, info
    headline: str
    loss_framing: str
    gain_framing: str
    cost_of_inaction: CostOfInaction | None = None
    deadline_pressure: int | None = None  # days until consequence
    social_proof: str | None = None
    call_to_action: str
    related_entity: NudgeRelatedEntity | None = None

    model_config = ConfigDict(from_attributes=True)


class NudgeListRead(BaseModel):
    """List of nudges for a building or portfolio."""

    entity_id: UUID
    nudges: list[NudgeRead]
    total: int
    context: str = "dashboard"

    model_config = ConfigDict(from_attributes=True)
