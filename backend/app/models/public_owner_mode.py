import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PublicOwnerOperatingMode(Base):
    __tablename__ = "public_owner_operating_modes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True, index=True
    )
    mode_type = Column(String(30), nullable=False)  # municipal | cantonal | federal | public_foundation | mixed
    is_active = Column(Boolean, default=True)
    governance_level = Column(String(20), default="standard")  # standard | enhanced | strict
    requires_committee_review = Column(Boolean, default=False)
    requires_review_pack = Column(Boolean, default=True)
    default_review_audience = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    organization = relationship("Organization")
