"""Post-work item tracking model for contractor completion verification."""

import uuid

from sqlalchemy import JSON, UUID, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PostWorkItem(Base):
    """Track completion of work items by contractors with photo evidence."""

    __tablename__ = "post_work_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    work_item_id = Column(UUID(as_uuid=True), nullable=True)  # Link to WorkItem if exists
    building_element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=True)

    # Completion tracking
    completion_status = Column(String(50), default="pending")  # pending, in_progress, completed, verified
    completion_date = Column(DateTime, nullable=True)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Photo evidence
    photo_uris = Column(JSON, nullable=True)  # [url1, url2, ...] - list of photo URIs
    before_after_pairs = Column(JSON, nullable=True)  # [{before_photo_id, after_photo_id}, ...]

    # Notes and metadata
    notes = Column(Text, nullable=True)
    verification_score = Column(Float, default=0.0)  # 0-100 confidence score
    flagged_for_review = Column(Boolean, default=False)
    ai_generated = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    building = relationship("Building")
    contractor = relationship("User", foreign_keys=[contractor_id])

    __table_args__ = (
        Index("idx_post_work_building_contractor", "building_id", "contractor_id"),
        Index("idx_post_work_status", "completion_status"),
    )


class WorksCompletionCertificate(Base):
    """PDF certificate issued when all work items are verified."""

    __tablename__ = "works_completion_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, unique=True)

    # Certificate details
    pdf_uri = Column(String(500), nullable=False)
    total_items = Column(Integer, nullable=False)  # Total work items in scope
    verified_items = Column(Integer, nullable=False)  # Verified items count
    completion_percentage = Column(Float, nullable=False)  # 0-100
    issued_date = Column(DateTime, default=func.now(), nullable=False)
    contractor_signature_uri = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    building = relationship("Building")

    __table_args__ = (Index("idx_cert_building", "building_id"),)
