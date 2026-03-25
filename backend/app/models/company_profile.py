"""BatiConnect — Marketplace: Company Profile model."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True, index=True
    )
    company_name = Column(String(300), nullable=False)
    legal_form = Column(String(50), nullable=True)  # SA | Sarl | raison_individuelle | other
    uid_number = Column(String(20), nullable=True)  # Swiss UID (CHE-xxx.xxx.xxx)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(10), nullable=True)
    canton = Column(String(2), nullable=True)
    contact_email = Column(String(200), nullable=False)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    work_categories = Column(JSON, nullable=False, default=list)
    certifications = Column(JSON, nullable=True)
    regions_served = Column(JSON, nullable=True)
    employee_count = Column(Integer, nullable=True)
    years_experience = Column(Integer, nullable=True)
    insurance_info = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    profile_completeness = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    organization = relationship("Organization", foreign_keys=[organization_id])
    verification = relationship("CompanyVerification", back_populates="company_profile")
    subscription = relationship("CompanySubscription", back_populates="company_profile", uselist=False)
