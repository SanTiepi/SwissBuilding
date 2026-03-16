"""Expert review, disagreement, and override governance."""

import uuid

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class ExpertReview(Base):
    __tablename__ = "expert_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # What is being reviewed
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    building_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # Review decision
    decision = Column(String(50), nullable=False)
    confidence_level = Column(String(20), nullable=True)
    justification = Column(Text, nullable=False)
    # Override details
    override_value = Column(JSON, nullable=True)
    original_value = Column(JSON, nullable=True)
    # Governance
    reviewed_by = Column(UUID(as_uuid=True), nullable=False)
    reviewer_role = Column(String(50), nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    # State
    status = Column(String(50), default="active")
    superseded_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
