import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Sample(Base):
    __tablename__ = "samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnostic_id = Column(UUID(as_uuid=True), ForeignKey("diagnostics.id"), nullable=False, index=True)
    sample_number = Column(String(50), nullable=False)
    location_floor = Column(String(50), nullable=True)
    location_room = Column(String(100), nullable=True)
    location_detail = Column(String(255), nullable=True)
    material_category = Column(String(100), nullable=True)
    material_description = Column(String(255), nullable=True)
    material_state = Column(String(50), nullable=True)
    pollutant_type = Column(String(50), nullable=True)
    pollutant_subtype = Column(String(100), nullable=True)
    concentration = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)
    threshold_exceeded = Column(Boolean, default=False)
    risk_level = Column(String(20), nullable=True)
    cfst_work_category = Column(String(20), nullable=True)
    action_required = Column(String(50), nullable=True)
    waste_disposal_type = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    diagnostic = relationship("Diagnostic", back_populates="samples")
