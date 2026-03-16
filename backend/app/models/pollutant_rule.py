import uuid

from sqlalchemy import Boolean, Column, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class PollutantRule(Base):
    __tablename__ = "pollutant_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pollutant = Column(String(50), nullable=False, index=True)
    material_category = Column(String(100), nullable=True)
    risk_start_year = Column(Integer, nullable=True)
    risk_end_year = Column(Integer, nullable=True)
    threshold_value = Column(Float, nullable=True)
    threshold_unit = Column(String(20), nullable=True)
    diagnostic_required = Column(Boolean, default=True)
    legal_reference = Column(String(255), nullable=True)
    action_if_exceeded = Column(String(500), nullable=True)
    waste_disposal_type = Column(String(20), nullable=True)
    cfst_default_category = Column(String(20), nullable=True)
    canton_specific = Column(String(2), nullable=True)
    description_fr = Column(Text, nullable=True)
    description_de = Column(Text, nullable=True)
