"""Schemas for AI feedback loop — correction recording + metrics."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AIFeedbackCreate(BaseModel):
    """Record a field-level AI correction."""

    entity_type: str  # diagnostic | material | sample
    entity_id: UUID | None = None  # defaults to diagnostic_id from path
    field_name: str  # e.g. "material_type", "hazard_level"
    original_value: str
    corrected_value: str
    model_version: str | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AIFeedbackRead(BaseModel):
    """AI feedback record."""

    id: UUID
    feedback_type: str
    entity_type: str
    entity_id: UUID
    field_name: str | None = None
    original_value: str | None = None
    corrected_value: str | None = None
    confidence_delta: float | None = None
    model_version: str | None = None
    user_id: UUID
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommonErrorEntry(BaseModel):
    original: str
    corrected: str
    count: int


class AIMetricsRead(BaseModel):
    """Aggregated AI accuracy metrics per entity_type + field_name."""

    id: UUID
    entity_type: str
    field_name: str
    total_extractions: int
    total_corrections: int
    error_rate: float
    common_errors: list[CommonErrorEntry] = []
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIMetricsSummary(BaseModel):
    """Dashboard-level summary across all fields."""

    overall_accuracy: float
    total_extractions: int
    total_corrections: int
    metrics: list[AIMetricsRead] = []

    model_config = ConfigDict(from_attributes=True)
