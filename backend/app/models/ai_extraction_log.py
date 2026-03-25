"""BatiConnect — AI Extraction Log model."""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class AIExtractionLog(Base):
    __tablename__ = "ai_extraction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_type = Column(String(50), nullable=False)  # quote_pdf | completion_report | certificate | document
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    source_filename = Column(String(500), nullable=True)
    input_hash = Column(String(64), nullable=False)  # SHA-256 of input
    output_data = Column(JSON, nullable=True)  # structured extraction result
    confidence_score = Column(Float, nullable=True)  # 0.0-1.0
    ai_model = Column(String(50), nullable=True)
    ambiguous_fields = Column(JSON, nullable=True)  # [{field, reason}]
    unknown_fields = Column(JSON, nullable=True)  # [{field}]
    status = Column(String(20), nullable=False, default="draft")  # draft | confirmed | corrected | rejected
    confirmed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_ai_extraction_logs_type", "extraction_type"),
        Index("idx_ai_extraction_logs_status", "status"),
        Index("idx_ai_extraction_logs_hash", "input_hash"),
    )
