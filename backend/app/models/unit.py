import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Unit(Base):
    __tablename__ = "units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    unit_type = Column(
        String(30), nullable=False
    )  # residential | commercial | parking | storage | office | common_area
    reference_code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    floor = Column(Integer, nullable=True)
    surface_m2 = Column(Float, nullable=True)
    rooms = Column(Float, nullable=True)
    status = Column(String(20), default="active")  # active | vacant | renovating | decommissioned
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="units")
    unit_zones = relationship("UnitZone", back_populates="unit", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("reference_code", "building_id", name="uq_unit_reference_building"),)
