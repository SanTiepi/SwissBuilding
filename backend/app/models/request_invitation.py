"""BatiConnect — Marketplace: Request Invitation model."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RequestInvitation(Base):
    __tablename__ = "request_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_request_id = Column(UUID(as_uuid=True), ForeignKey("client_requests.id"), nullable=False, index=True)
    company_profile_id = Column(UUID(as_uuid=True), ForeignKey("company_profiles.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | viewed | accepted | declined | expired
    sent_at = Column(DateTime, nullable=False, default=func.now())
    viewed_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    decline_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    client_request = relationship("ClientRequest", back_populates="invitations")
    company_profile = relationship("CompanyProfile")
