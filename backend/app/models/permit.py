"""Permit workflow integration for remediation projects."""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PermitStatus(str, Enum):
    """Permit lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Permit(Base):
    """Building permit for renovation, subsidy, or declaration."""

    __tablename__ = "permits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    permit_type = Column(
        String(50), nullable=False
    )  # renovation | subsidy | declaration
    status = Column(SQLEnum(PermitStatus), nullable=False, default=PermitStatus.PENDING)
    issued_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    subsidy_amount = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship
    building = relationship("Building", back_populates="permits")
