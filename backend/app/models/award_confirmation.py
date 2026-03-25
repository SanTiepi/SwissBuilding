"""BatiConnect — Marketplace: Award Confirmation model."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AwardConfirmation(Base):
    __tablename__ = "award_confirmations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_request_id = Column(UUID(as_uuid=True), ForeignKey("client_requests.id"), nullable=False, index=True)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False, index=True)
    company_profile_id = Column(UUID(as_uuid=True), ForeignKey("company_profiles.id"), nullable=False, index=True)
    awarded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    award_amount_chf = Column(Numeric(12, 2), nullable=True)
    conditions = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    awarded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    client_request = relationship("ClientRequest")
    quote = relationship("Quote")
    company_profile = relationship("CompanyProfile")
    awarded_by_user = relationship("User", foreign_keys=[awarded_by_user_id])
    completion_confirmation = relationship("CompletionConfirmation", back_populates="award_confirmation", uselist=False)
