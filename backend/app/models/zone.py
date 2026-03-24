import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    parent_zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    zone_type = Column(String(30), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    floor_number = Column(Integer, nullable=True)
    surface_area_m2 = Column(Float, nullable=True)
    usage_type = Column(String(30), nullable=True)  # residential | commercial | storage | parking | technical | common
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="zones")
    parent_zone = relationship("Zone", remote_side=[id], back_populates="children")
    children = relationship("Zone", back_populates="parent_zone")
    elements = relationship("BuildingElement", back_populates="zone", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_zones_building_id", "building_id"),
        Index("idx_zones_building_id_zone_type", "building_id", "zone_type"),
    )
