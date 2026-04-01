import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ReviewTask(Base):
    """A pending human review/validation task."""

    __tablename__ = "review_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # What needs review
    task_type = Column(String(50), nullable=False)
    # Types: extraction_review, claim_verification, contradiction_resolution,
    #        decision_approval, publication_review, transfer_approval,
    #        pack_review, source_validation, ritual_approval

    target_type = Column(String(50), nullable=False)  # extraction, claim, decision, pack, passport, etc.
    target_id = Column(UUID(as_uuid=True), nullable=False)

    # Context
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)

    # Priority
    priority = Column(String(20), default="medium")  # critical, high, medium, low

    # Assignment
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, in_progress, completed, skipped, escalated

    # Resolution
    completed_at = Column(DateTime, nullable=True)
    completed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution = Column(String(20), nullable=True)  # approved, rejected, corrected, escalated
    resolution_note = Column(Text, nullable=True)

    # Escalation
    escalation_reason = Column(Text, nullable=True)
    escalated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building")
    organization = relationship("Organization")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])

    __table_args__ = (
        Index("idx_review_tasks_org_status", "organization_id", "status"),
        Index("idx_review_tasks_building", "building_id"),
        Index("idx_review_tasks_target", "target_type", "target_id"),
        Index("idx_review_tasks_priority", "priority"),
        Index("idx_review_tasks_assigned", "assigned_to_id"),
    )
