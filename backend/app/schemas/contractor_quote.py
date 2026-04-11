"""Schemas for Contractor Quote Extraction."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractorQuoteCreate(BaseModel):
    """Create contractor quote from extraction."""

    document_id: UUID
    building_id: UUID
    contractor_name: str | None = None
    contractor_contact: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    total_price: float | None = None
    currency: str = "CHF"
    scope: str | None = None
    work_type: str | None = None
    timeline: str | None = None
    validity_days: str | None = None
    conditions: str | None = None
    ai_generated: str = "claude-sonnet"
    confidence: float = Field(ge=0, le=1)
    confidence_breakdown: dict[str, float] | None = None
    raw_extraction: dict | None = None


class ContractorQuoteRead(BaseModel):
    """Read contractor quote."""

    id: UUID
    document_id: UUID
    building_id: UUID
    contractor_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    total_price: float | None = None
    currency: str
    scope: str | None = None
    work_type: str | None = None
    timeline: str | None = None
    ai_generated: str
    confidence: float
    reviewed: str
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractorQuoteUpdate(BaseModel):
    """Update contractor quote review status."""

    reviewed: str = Field(..., pattern="^(pending|confirmed|disputed)$")
    reviewer_notes: str | None = None


class ContractorQuoteList(BaseModel):
    """Contractor quote list item."""

    id: UUID
    document_id: UUID
    contractor_name: str | None = None
    total_price: float | None = None
    confidence: float
    reviewed: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
