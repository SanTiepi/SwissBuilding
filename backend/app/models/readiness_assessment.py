import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ReadinessAssessment(Base):
    __tablename__ = "readiness_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    readiness_type = Column(String(50), nullable=False)

    # Assessment
    status = Column(String(20), nullable=False)
    score = Column(Float, nullable=True)

    # Evidence
    checks_json = Column(JSON, nullable=True)
    blockers_json = Column(JSON, nullable=True)
    conditions_json = Column(JSON, nullable=True)

    # Validity
    assessed_at = Column(DateTime, default=func.now())
    valid_until = Column(DateTime, nullable=True)
    assessed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)

    building = relationship("Building")

    __table_args__ = (Index("idx_readiness_building_type", "building_id", "readiness_type"),)
