"""Schemas for the hybrid document classification pipeline."""

from pydantic import BaseModel, ConfigDict


class ClassificationCandidate(BaseModel):
    """A candidate document type with confidence score."""

    type: str
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class ClassificationResult(BaseModel):
    """Result from classifying a single document."""

    document_id: str | None = None
    document_type: str
    confidence: float
    method: str  # filename | content | hybrid
    candidates: list[ClassificationCandidate]
    ai_generated: bool = True
    keywords_found: list[str]

    model_config = ConfigDict(from_attributes=True)


class BatchClassificationResult(BaseModel):
    """Summary of batch classification for a building."""

    building_id: str
    total_processed: int
    classified_count: int
    unclassified_count: int
    results: list[ClassificationResult]

    model_config = ConfigDict(from_attributes=True)


class DocumentTypeInfo(BaseModel):
    """Info about a supported document type."""

    type_key: str
    label_fr: str
    label_en: str
    label_de: str
    label_it: str
    keywords: list[str]

    model_config = ConfigDict(from_attributes=True)
