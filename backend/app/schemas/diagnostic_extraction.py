"""Pydantic schemas for the diagnostic extraction pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DiagnosticExtractionRead(BaseModel):
    id: UUID
    document_id: UUID
    building_id: UUID
    created_by_id: UUID
    status: str
    confidence: float | None
    extracted_data: dict[str, Any] | None
    corrections: list[dict[str, Any]] | None
    applied_at: datetime | None
    reviewed_by_id: UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DiagnosticExtractionReview(BaseModel):
    """Payload for reviewing/updating an extraction before applying."""

    extracted_data: dict[str, Any] | None = None


class DiagnosticExtractionApplyResponse(BaseModel):
    diagnostic_id: str
    sample_ids: list[str]
    evidence_link_id: str


class DiagnosticExtractionCorrectionCreate(BaseModel):
    field_path: str
    old_value: Any = None
    new_value: Any = None


class DiagnosticExtractionRejectRequest(BaseModel):
    reason: str | None = None
