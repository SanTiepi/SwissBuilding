"""BatiConnect — Contractor Quote Extraction — automatic parsing of contractor estimates from PDFs."""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ContractorQuote(Base):
    """Automatic extraction of contractor quotes (devis) from PDFs."""

    __tablename__ = "contractor_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # Extracted fields
    contractor_name = Column(String(500), nullable=True)  # Company/contractor name
    contractor_contact = Column(String(500), nullable=True)  # Email, phone, address
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Financial fields
    total_price = Column(Numeric(12, 2), nullable=True)  # CHF
    currency = Column(String(3), nullable=False, default="CHF")
    price_per_unit = Column(Numeric(12, 2), nullable=True)
    unit = Column(String(50), nullable=True)  # m², day, etc.
    vat_included = Column(String(50), nullable=True)  # "yes", "no", "unknown"

    # Scope & timeline
    scope = Column(Text, nullable=True)  # Description of work/services
    work_type = Column(String(100), nullable=True)  # asbestos_removal, lead_paint_removal, etc.
    timeline = Column(String(255), nullable=True)  # e.g. "3 weeks", "15 days", "2-4 weeks"
    start_date = Column(DateTime, nullable=True)  # If extraction could parse a date
    end_date = Column(DateTime, nullable=True)

    # Validity & conditions
    validity_days = Column(String(100), nullable=True)  # e.g. "30 days", "60 days"
    conditions = Column(Text, nullable=True)  # Payment terms, warranties, etc.

    # AI extraction metadata
    ai_generated = Column(String(50), nullable=False, default="claude-sonnet")  # model name
    confidence = Column(Float, nullable=False, default=0.5)  # 0-1.0 confidence score
    confidence_breakdown = Column(JSON, nullable=True)  # {field: confidence} for each field
    raw_extraction = Column(JSON, nullable=True)  # Full LLM response for debugging

    # Review status
    reviewed = Column(String(20), nullable=False, server_default="pending")  # pending | confirmed | disputed
    reviewer_notes = Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_contractor_quote_document", "document_id"),
        Index("idx_contractor_quote_building", "building_id"),
        Index("idx_contractor_quote_confidence", "confidence"),
        Index("idx_contractor_quote_reviewed", "reviewed"),
    )

    # Relationships
    document = relationship("Document")
    building = relationship("Building")
    reviewer = relationship("User")
