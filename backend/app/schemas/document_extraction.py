"""Schemas for document extraction (GED B)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ExtractionField(BaseModel):
    """Single extracted field from document text."""

    field: str
    value: str
    raw_match: str
    position: int
    confidence: float
    ai_generated: bool = True

    model_config = ConfigDict(from_attributes=True)


class ExtractionResult(BaseModel):
    """Full extraction result for a document."""

    document_id: str
    total_fields: int
    field_counts: dict[str, int]
    extractions: dict[str, list[ExtractionField]]

    model_config = ConfigDict(from_attributes=True)
