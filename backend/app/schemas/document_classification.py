import uuid

from pydantic import BaseModel, ConfigDict


class DocumentClassification(BaseModel):
    document_id: uuid.UUID
    filename: str
    document_category: str
    pollutant_tags: list[str]
    confidence: float
    suggested_tags: list[str]

    model_config = ConfigDict(from_attributes=True)


class ClassificationSummary(BaseModel):
    building_id: uuid.UUID
    total_documents: int
    category_counts: dict[str, int]
    pollutant_coverage: dict[str, bool]
    coverage_gaps: list[str]

    model_config = ConfigDict(from_attributes=True)


class MissingDocumentSuggestion(BaseModel):
    category: str
    pollutant: str | None = None
    reason: str
    priority: str  # high | medium | low

    model_config = ConfigDict(from_attributes=True)
