"""SwissRules Watch — RuleSource model."""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RuleSource(Base):
    __tablename__ = "rule_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_code = Column(String(50), unique=True, nullable=False)
    source_name = Column(String(200), nullable=False)
    source_url = Column(String(500), nullable=True)
    watch_tier = Column(String(10), nullable=False)  # daily|weekly|monthly|quarterly
    last_checked_at = Column(DateTime, nullable=True)
    last_changed_at = Column(DateTime, nullable=True)
    freshness_state = Column(String(20), nullable=False, default="unknown")  # current|aging|stale|unknown
    change_types_detected = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    change_events = relationship("RuleChangeEvent", back_populates="source", cascade="all, delete-orphan")
