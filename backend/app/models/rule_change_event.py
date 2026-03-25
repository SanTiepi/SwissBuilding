"""SwissRules Watch — RuleChangeEvent model."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RuleChangeEvent(Base):
    __tablename__ = "rule_change_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("rule_sources.id"), nullable=False)
    event_type = Column(
        String(30), nullable=False
    )  # new_rule|amended_rule|repealed_rule|portal_change|form_change|procedure_change
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    impact_summary = Column(String(500), nullable=True)
    detected_at = Column(DateTime, nullable=False, default=func.now())
    reviewed = Column(Boolean, default=False)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    affects_buildings = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    source = relationship("RuleSource", back_populates="change_events")
