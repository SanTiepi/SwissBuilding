"""BatiConnect -- DiagnosticExtraction: pending extraction from a diagnostic PDF, awaiting human review.

Follows the parse -> review -> apply pattern. Never auto-persisted.
"""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class DiagnosticExtraction(Base):
    __tablename__ = "diagnostic_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="draft")  # draft | reviewed | applied | rejected
    confidence = Column(Float, nullable=True)  # 0.0-1.0 overall
    extracted_data = Column(JSON, nullable=True)  # full extraction result
    corrections = Column(JSON, nullable=True)  # [{field_path, old_value, new_value, corrected_by_id, timestamp}]
    applied_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_diag_extraction_document", "document_id"),
        Index("idx_diag_extraction_status", "status"),
        Index("idx_diag_extraction_building", "building_id"),
    )
