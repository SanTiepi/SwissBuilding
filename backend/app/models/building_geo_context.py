"""BuildingGeoContext — cached geo.admin overlay data for a building."""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingGeoContext(Base):
    __tablename__ = "building_geo_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, unique=True, index=True)
    context_data = Column(JSON, nullable=False, default=dict)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    source_version = Column(String(50), nullable=False, default="geo.admin-v1")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    building = relationship("Building", foreign_keys=[building_id])
