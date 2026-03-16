import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PostWorksState(Base):
    __tablename__ = "post_works_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("interventions.id"), nullable=True, index=True)

    # What changed
    state_type = Column(String(50), nullable=False)
    pollutant_type = Column(String(20), nullable=True)

    # Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Related entities
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)

    # Evidence
    verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    evidence_json = Column(Text, nullable=True)

    # Metadata
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    recorded_at = Column(DateTime, default=func.now())
    notes = Column(Text, nullable=True)

    building = relationship("Building")
    intervention = relationship("Intervention")

    __table_args__ = (
        Index("idx_post_works_building_id", "building_id"),
        Index("idx_post_works_intervention_id", "intervention_id"),
    )
