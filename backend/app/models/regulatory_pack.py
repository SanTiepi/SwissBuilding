import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RegulatoryPack(Base):
    __tablename__ = "regulatory_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False)
    pollutant_type = Column(String(50), nullable=False)  # asbestos, pcb, lead, hap, radon
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)

    # Thresholds
    threshold_value = Column(Float, nullable=True)
    threshold_unit = Column(String(30), nullable=True)
    threshold_action = Column(String(50), nullable=True)  # "monitor", "remediate", "immediate_removal"

    # Risk calibration
    risk_year_start = Column(Integer, nullable=True)  # e.g., pre-1990 for asbestos
    risk_year_end = Column(Integer, nullable=True)
    base_probability = Column(Float, nullable=True)  # 0.0 to 1.0

    # Work categories (JSON for flexibility)
    work_categories_json = Column(JSON, nullable=True)  # CFST-like work categories
    waste_classification_json = Column(JSON, nullable=True)  # OLED-like waste types

    # Legal references
    legal_reference = Column(String(500), nullable=True)
    legal_url = Column(String(500), nullable=True)
    description_fr = Column(Text, nullable=True)
    description_de = Column(Text, nullable=True)
    description_it = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)

    # Notification requirements
    notification_required = Column(Boolean, default=False)
    notification_authority = Column(String(255), nullable=True)
    notification_delay_days = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    jurisdiction = relationship("Jurisdiction", back_populates="regulatory_packs")
