import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingRiskScore(Base):
    __tablename__ = "building_risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), unique=True, nullable=False)
    asbestos_probability = Column(Float, default=0.0)
    pcb_probability = Column(Float, default=0.0)
    lead_probability = Column(Float, default=0.0)
    hap_probability = Column(Float, default=0.0)
    radon_probability = Column(Float, default=0.0)
    overall_risk_level = Column(String(20), default="unknown")
    confidence = Column(Float, default=0.0)
    factors_json = Column(JSON, nullable=True)
    data_source = Column(String(50), default="model")
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="risk_scores")
