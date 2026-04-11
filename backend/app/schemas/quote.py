"""Quote extraction schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuoteItemRead(BaseModel):
    """Extracted quote line item."""

    description: str
    qty: float | None = None
    unit_price: float | None = None
    total: float | None = None
    unit: str | None = None


class QuoteCreate(BaseModel):
    """Create a quote manually."""

    building_id: UUID
    company_name: str
    amount_chf: float
    items: list[QuoteItemRead] = Field(default_factory=list)
    validity_date: datetime | None = None
    notes: str | None = None


class QuoteRead(BaseModel):
    """Quote extraction response."""

    id: UUID
    building_id: UUID
    company_name: str
    amount_chf: float
    items: list[dict] | None = None
    extraction_confidence: float = 0.0
    extracted_date: datetime | None = None
    validity_date: datetime | None = None
    ai_generated: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class QuoteListRead(BaseModel):
    """Quote list item."""

    id: UUID
    company_name: str
    amount_chf: float
    item_count: int = 0
    extraction_confidence: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True
