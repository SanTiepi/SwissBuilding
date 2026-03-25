"""Commune Adapter — CommunalRuleOverride model."""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CommunalRuleOverride(Base):
    __tablename__ = "communal_rule_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commune_code = Column(String(10), nullable=False)
    canton_code = Column(String(2), nullable=False)
    override_type = Column(
        String(30), nullable=False
    )  # stricter_threshold|additional_requirement|local_procedure|heritage_constraint
    rule_reference = Column(String(200), nullable=True)
    impact_summary = Column(String(500), nullable=False)
    review_required = Column(Boolean, default=True)
    confidence_level = Column(
        String(20), nullable=False, default="review_required"
    )  # auto_safe|auto_with_notice|review_required|blocked
    source_id = Column(UUID(as_uuid=True), ForeignKey("rule_sources.id"), nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    source = relationship("RuleSource")
