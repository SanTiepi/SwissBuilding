"""BatiConnect — Marketplace: Review model."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    completion_confirmation_id = Column(
        UUID(as_uuid=True), ForeignKey("completion_confirmations.id"), nullable=False, index=True
    )
    client_request_id = Column(UUID(as_uuid=True), ForeignKey("client_requests.id"), nullable=False, index=True)
    company_profile_id = Column(UUID(as_uuid=True), ForeignKey("company_profiles.id"), nullable=False, index=True)
    reviewer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewer_type = Column(String(20), nullable=False)  # client | company
    rating = Column(Integer, nullable=False)  # 1-5
    quality_score = Column(Integer, nullable=True)  # 1-5
    timeliness_score = Column(Integer, nullable=True)  # 1-5
    communication_score = Column(Integer, nullable=True)  # 1-5
    comment = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")  # draft|submitted|under_moderation|published|rejected
    moderated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    moderated_at = Column(DateTime, nullable=True)
    moderation_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    completion_confirmation = relationship("CompletionConfirmation")
    client_request = relationship("ClientRequest")
    company_profile = relationship("CompanyProfile")
    reviewer_user = relationship("User", foreign_keys=[reviewer_user_id])
    moderated_by_user = relationship("User", foreign_keys=[moderated_by_user_id])
