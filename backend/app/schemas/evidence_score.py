"""Pydantic v2 schemas for the Evidence Score."""

from pydantic import BaseModel, ConfigDict


class EvidenceScoreBreakdown(BaseModel):
    """Weighted contribution of each dimension."""

    trust_weighted: float
    completeness_weighted: float
    freshness_weighted: float
    gap_penalty_weighted: float

    model_config = ConfigDict(from_attributes=True)


class EvidenceScoreRead(BaseModel):
    """Unified evidence score (0-100) for a building."""

    building_id: str
    score: int
    grade: str  # A, B, C, D, F
    trust: float
    completeness: float
    freshness: float
    gap_penalty: float
    breakdown: EvidenceScoreBreakdown
    computed_at: str

    model_config = ConfigDict(from_attributes=True)
