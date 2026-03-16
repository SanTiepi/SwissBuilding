import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    decision_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    rationale = Column(Text, nullable=False)
    alternatives_considered = Column(Text, nullable=True)
    decided_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    decided_at = Column(DateTime, nullable=False, default=func.now())
    context_snapshot = Column(JSON, nullable=True)
    outcome = Column(String(50), nullable=True)
    outcome_notes = Column(Text, nullable=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    user = relationship("User")

    __table_args__ = (
        Index("idx_decision_records_building_id", "building_id"),
        Index("idx_decision_records_decided_at", "decided_at"),
    )
