"""BatiConnect — AI Rule Pattern model for pattern learning."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class AIRulePattern(Base):
    __tablename__ = "ai_rule_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern_type = Column(
        String(50), nullable=False
    )  # extraction_rule | contradiction_signal | remediation_outcome | readiness_hint
    source_entity_type = Column(String(50), nullable=False)  # what generated this pattern
    rule_key = Column(String(200), nullable=False)  # e.g. "quote_pdf:scope_extraction:asbestos_removal"
    rule_definition = Column(JSON, nullable=True)  # {condition, action, confidence_threshold}
    sample_count = Column(Integer, nullable=False, default=0)
    last_confirmed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
