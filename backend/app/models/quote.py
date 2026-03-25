"""BatiConnect — Marketplace: Quote model."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_request_id = Column(UUID(as_uuid=True), ForeignKey("client_requests.id"), nullable=False, index=True)
    company_profile_id = Column(UUID(as_uuid=True), ForeignKey("company_profiles.id"), nullable=False, index=True)
    invitation_id = Column(UUID(as_uuid=True), ForeignKey("request_invitations.id"), nullable=True)
    amount_chf = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="CHF")
    validity_days = Column(Integer, nullable=False, default=30)
    description = Column(Text, nullable=True)
    work_plan = Column(Text, nullable=True)
    timeline_weeks = Column(Integer, nullable=True)
    includes = Column(JSON, nullable=True)  # ["mobilization","waste_disposal","air_monitoring","final_report"]
    excludes = Column(JSON, nullable=True)  # ["scaffolding","permits"]
    status = Column(String(20), nullable=False, default="draft")  # draft | submitted | withdrawn | awarded | rejected
    submitted_at = Column(DateTime, nullable=True)
    content_hash = Column(String(64), nullable=True)  # SHA-256 of quote content at submission
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    client_request = relationship("ClientRequest", back_populates="quotes")
    company_profile = relationship("CompanyProfile")
    invitation = relationship("RequestInvitation")
