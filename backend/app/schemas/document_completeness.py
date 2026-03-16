"""Schemas for document completeness assessment."""

import uuid

from pydantic import BaseModel, ConfigDict


class DocumentTypeStatus(BaseModel):
    """Status of a single required document type."""

    document_type: str
    status: str  # present | missing | outdated
    document_id: uuid.UUID | None = None
    uploaded_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentCompletenessResult(BaseModel):
    """Overall document completeness assessment for a building."""

    building_id: uuid.UUID
    score: float  # 0-100
    total_required: int
    present: int
    missing: int
    outdated: int
    types: list[DocumentTypeStatus]

    model_config = ConfigDict(from_attributes=True)


class MissingDocumentDetail(BaseModel):
    """Prioritized detail about a missing document."""

    document_type: str
    reason: str
    provider: str  # who should provide it
    urgency: str  # critical | high | medium | low
    template_available: bool

    model_config = ConfigDict(from_attributes=True)


class DocumentCurrencyFlag(BaseModel):
    """Flag for a document that may be outdated."""

    document_id: uuid.UUID
    document_type: str
    filename: str
    uploaded_at: str
    max_validity_years: int
    age_years: float
    is_expired: bool
    expires_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentCurrencyResult(BaseModel):
    """Currency validation result for a building's documents."""

    building_id: uuid.UUID
    total_checked: int
    valid: int
    expired: int
    flags: list[DocumentCurrencyFlag]

    model_config = ConfigDict(from_attributes=True)


class BuildingDocumentGap(BaseModel):
    """Document gap summary for a single building."""

    building_id: uuid.UUID
    address: str
    score: float
    missing_count: int
    critical_missing: list[str]

    model_config = ConfigDict(from_attributes=True)


class PortfolioDocumentStatus(BaseModel):
    """Organization-level document completeness overview."""

    organization_id: uuid.UUID
    total_buildings: int
    average_score: float
    most_commonly_missing: str | None = None
    buildings_with_critical_gaps: list[BuildingDocumentGap]
    estimated_documents_to_full: int

    model_config = ConfigDict(from_attributes=True)
