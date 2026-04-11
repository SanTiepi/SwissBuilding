"""Pydantic v2 schemas for Sampling Quality Score."""

from pydantic import BaseModel, ConfigDict


class SamplingCriterionRead(BaseModel):
    """Single criterion result."""

    name: str
    score: int
    max: int
    detail: str
    recommendation: str

    model_config = ConfigDict(from_attributes=True)


class SamplingQualityRead(BaseModel):
    """Per-diagnostic sampling quality score."""

    diagnostic_id: str
    overall_score: int
    grade: str  # A, B, C, D, F
    criteria: list[SamplingCriterionRead]
    confidence_level: str  # high, medium, low, very_low
    warnings: list[str]
    evaluated_at: str

    model_config = ConfigDict(from_attributes=True)


class BuildingSamplingQualityRead(BaseModel):
    """Building-level aggregate of sampling quality across diagnostics."""

    building_id: str
    avg_score: int
    worst_diagnostic: str | None
    best_diagnostic: str | None
    diagnostics: list[SamplingQualityRead]
    evaluated_at: str

    model_config = ConfigDict(from_attributes=True)
