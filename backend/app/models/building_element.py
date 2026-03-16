import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingElement(Base):
    __tablename__ = "building_elements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False, index=True)
    element_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    condition = Column(String(20), nullable=True)
    installation_year = Column(Integer, nullable=True)
    last_inspected_at = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    zone = relationship("Zone", back_populates="elements")
    materials = relationship("Material", back_populates="element", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_building_elements_zone_id", "zone_id"),
        Index("idx_building_elements_zone_id_element_type", "zone_id", "element_type"),
    )
