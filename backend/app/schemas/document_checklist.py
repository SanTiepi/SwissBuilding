"""Schemas for document checklist (GED C)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ChecklistItemRead(BaseModel):
    """Single checklist item."""

    document_type: str
    label: str
    importance: str  # critical | high | medium | low
    legal_basis: str | None = None
    status: str  # present | missing | expired | not_applicable
    document_id: str | None = None
    uploaded_at: str | None = None
    recommendation: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentChecklistRead(BaseModel):
    """Full document checklist for a building."""

    building_id: str
    total_required: int
    total_present: int
    completion_pct: float
    items: list[ChecklistItemRead]
    critical_missing: list[str]
    evaluated_at: str

    model_config = ConfigDict(from_attributes=True)
