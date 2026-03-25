"""BatiConnect — Marketplace: Company Verification model."""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class CompanyVerification(Base):
    __tablename__ = "company_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_profile_id = Column(UUID(as_uuid=True), ForeignKey("company_profiles.id"), nullable=False, index=True)
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending | in_review | approved | rejected | suspended | expired
    verified_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_type = Column(String(30), nullable=False, default="initial")  # initial | renewal | spot_check
    checks_performed = Column(JSON, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    valid_until = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    company_profile = relationship("CompanyProfile", back_populates="verification")
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
