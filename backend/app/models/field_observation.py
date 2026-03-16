import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class FieldObservation(Base):
    __tablename__ = "field_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=True)
    observer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    observation_type = Column(String(30), nullable=False)
    severity = Column(String(20), nullable=False, default="info")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location_description = Column(String(500), nullable=True)

    observed_at = Column(DateTime, nullable=False, default=func.now())
    photo_reference = Column(String(500), nullable=True)

    verified = Column(Boolean, default=False, nullable=False)
    verified_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    metadata_json = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", backref="field_observations")
    zone = relationship("Zone", backref="field_observations")
    element = relationship("BuildingElement", backref="field_observations")
    observer = relationship("User", foreign_keys=[observer_id], backref="field_observations_made")
    verifier = relationship("User", foreign_keys=[verified_by_id], backref="field_observations_verified")

    __table_args__ = (
        Index("idx_field_observations_building_id", "building_id"),
        Index("idx_field_observations_building_type", "building_id", "observation_type"),
        Index("idx_field_observations_building_severity", "building_id", "severity"),
        Index("idx_field_observations_building_status", "building_id", "status"),
    )
