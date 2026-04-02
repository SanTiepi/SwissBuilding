"""Building Passport — A-F grade system for holistic building assessment."""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class BuildingPassport(Base):
    """Standardized A-F report card for building condition, compliance, and readiness."""

    __tablename__ = "building_passports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # Version tracking for historical comparison
    version = Column(Integer, nullable=False, default=1)

    # Six category grades (A-F)
    structural_grade = Column(String(1), nullable=False)  # A-F
    energy_grade = Column(String(1), nullable=False)
    safety_grade = Column(String(1), nullable=False)
    environmental_grade = Column(String(1), nullable=False)
    compliance_grade = Column(String(1), nullable=False)
    readiness_grade = Column(String(1), nullable=False)

    # Overall grade (median of 6 categories)
    overall_grade = Column(String(1), nullable=False)

    # Metadata: which components contributed to each grade calculation
    metadata = Column(JSON, nullable=True)  # {components_used: {...}, calculation_date, notes}

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
