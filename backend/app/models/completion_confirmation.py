"""BatiConnect — Marketplace: Completion Confirmation model."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CompletionConfirmation(Base):
    __tablename__ = "completion_confirmations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    award_confirmation_id = Column(
        UUID(as_uuid=True), ForeignKey("award_confirmations.id"), nullable=False, unique=True, index=True
    )
    client_confirmed = Column(Boolean, default=False)
    client_confirmed_at = Column(DateTime, nullable=True)
    client_confirmed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    company_confirmed = Column(Boolean, default=False)
    company_confirmed_at = Column(DateTime, nullable=True)
    company_confirmed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending|client_confirmed|company_confirmed|fully_confirmed|disputed
    completion_notes = Column(Text, nullable=True)
    final_amount_chf = Column(Numeric(12, 2), nullable=True)
    content_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    award_confirmation = relationship("AwardConfirmation", back_populates="completion_confirmation")
    client_confirmed_by_user = relationship("User", foreign_keys=[client_confirmed_by_user_id])
    company_confirmed_by_user = relationship("User", foreign_keys=[company_confirmed_by_user_id])
