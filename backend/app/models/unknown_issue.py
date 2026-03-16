import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UnknownIssue(Base):
    __tablename__ = "unknown_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    unknown_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="open")

    # What is unknown
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Related entity
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Impact
    blocks_readiness = Column(Boolean, default=False)
    readiness_types_affected = Column(Text, nullable=True)

    # Resolution
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Metadata
    detected_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now())

    building = relationship("Building")

    __table_args__ = (Index("idx_unknown_issues_building_id", "building_id"),)
