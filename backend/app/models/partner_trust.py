"""BatiConnect — Partner Trust models.

PartnerTrustProfile: aggregated trust evaluation per partner organization.
PartnerTrustSignal: individual trust observations (delivery, evidence, response).
"""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PartnerTrustProfile(Base):
    __tablename__ = "partner_trust_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True, index=True)
    delivery_reliability_score = Column(Float, nullable=True)  # 0-1
    evidence_quality_score = Column(Float, nullable=True)  # 0-1
    responsiveness_score = Column(Float, nullable=True)  # 0-1
    overall_trust_level = Column(
        String(20), nullable=False, default="unknown"
    )  # strong | adequate | review | weak | unknown
    signal_count = Column(Integer, nullable=False, default=0)
    last_evaluated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    partner_org = relationship("Organization")


class PartnerTrustSignal(Base):
    __tablename__ = "partner_trust_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    signal_type = Column(
        String(30), nullable=False
    )  # delivery_success | delivery_failure | complement_triggered | evidence_rejected | response_fast | response_slow | evidence_clean | evidence_rework
    source_entity_type = Column(String(50), nullable=True)
    source_entity_id = Column(UUID(as_uuid=True), nullable=True)
    value = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=func.now())
    created_at = Column(DateTime, default=func.now())

    partner_org = relationship("Organization")
