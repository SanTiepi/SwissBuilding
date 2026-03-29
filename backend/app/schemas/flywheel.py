"""Schemas for the flywheel learning loop — classification & extraction feedback."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ClassificationFeedbackCreate(BaseModel):
    """Record a classification correction."""

    document_id: str
    predicted_type: str
    corrected_type: str

    model_config = ConfigDict(from_attributes=True)


class ExtractionFeedbackCreate(BaseModel):
    """Record an extraction correction or confirmation."""

    document_id: str
    field_name: str
    predicted_value: str
    corrected_value: str | None = None
    accepted: bool = False

    model_config = ConfigDict(from_attributes=True)


class PerTypeAccuracy(BaseModel):
    accuracy: float
    total: int
    correct: int


class ConfusionPair(BaseModel):
    predicted: str
    actual: str
    count: int


class AccuracyMetrics(BaseModel):
    """Classification or extraction accuracy metrics."""

    overall_accuracy: float
    total_predictions: int | None = None
    total_extractions: int | None = None
    total_corrections: int
    per_type_accuracy: dict[str, PerTypeAccuracy] | None = None
    per_field_accuracy: dict[str, PerTypeAccuracy] | None = None
    confusion_matrix: list[ConfusionPair] | None = None
    trend: str  # improving | stable | declining

    model_config = ConfigDict(from_attributes=True)


class LearnedRule(BaseModel):
    """A rule discovered from correction patterns."""

    predicted_type: str
    corrected_type: str
    occurrence_count: int
    confidence: float
    suggestion: str

    model_config = ConfigDict(from_attributes=True)


class FlywheelDashboardRead(BaseModel):
    """Aggregated flywheel dashboard metrics."""

    classification_accuracy: float
    extraction_accuracy: float
    total_documents_processed: int
    total_corrections: int
    correction_rate: float
    top_confusion_pairs: list[ConfusionPair]
    learned_rules_count: int
    learned_rules: list[LearnedRule]
    improvement_trend: str  # improving | stable | declining

    model_config = ConfigDict(from_attributes=True)
