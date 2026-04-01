import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=False, index=True)
    material_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    manufacturer = Column(String(255), nullable=True)
    installation_year = Column(Integer, nullable=True)
    contains_pollutant = Column(Boolean, default=False)
    pollutant_type = Column(String(50), nullable=True)
    pollutant_confirmed = Column(Boolean, default=False)
    sample_id = Column(UUID(as_uuid=True), ForeignKey("samples.id"), nullable=True)
    source = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    # AI recognition metadata
    identified_by_ai = Column(Boolean, default=False)
    ai_confidence = Column(Float, nullable=True)
    year_estimated = Column(Integer, nullable=True)
    ai_pollutants = Column(JSON, nullable=True)
    ai_recommendations = Column(JSON, nullable=True)

    element = relationship("BuildingElement", back_populates="materials")
    sample = relationship("Sample")

    __table_args__ = (
        Index("idx_materials_element_id", "element_id"),
        Index("idx_materials_element_id_contains_pollutant", "element_id", "contains_pollutant"),
    )
