"""BatiConnect — Marketplace: Company Subscription model."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CompanySubscription(Base):
    __tablename__ = "company_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_profile_id = Column(
        UUID(as_uuid=True), ForeignKey("company_profiles.id"), nullable=False, unique=True, index=True
    )
    plan_type = Column(String(30), nullable=False)  # free_trial | basic | professional | premium
    status = Column(String(20), nullable=False, default="active")  # active | expired | suspended | cancelled
    started_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_network_eligible = Column(Boolean, default=False)
    billing_reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    company_profile = relationship("CompanyProfile", back_populates="subscription")
