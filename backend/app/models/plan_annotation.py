import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class PlanAnnotation(Base):
    __tablename__ = "plan_annotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("technical_plans.id"), nullable=False, index=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # Annotation positioning (relative coordinates on the plan image)
    x = Column(Float, nullable=False)  # 0.0 - 1.0 relative position
    y = Column(Float, nullable=False)  # 0.0 - 1.0 relative position

    # Annotation content
    annotation_type = Column(String(30), nullable=False)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # References
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    sample_id = Column(UUID(as_uuid=True), ForeignKey("samples.id"), nullable=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=True)

    # Metadata
    color = Column(String(20), nullable=True)  # hex color for rendering
    icon = Column(String(50), nullable=True)  # icon identifier
    metadata_json = Column(JSON, nullable=True)

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    plan = relationship("TechnicalPlan")
    building = relationship("Building")
    zone = relationship("Zone")

    __table_args__ = (
        Index("idx_plan_annotations_plan_id", "plan_id"),
        Index("idx_plan_annotations_building_id", "building_id"),
        Index("idx_plan_annotations_plan_id_type", "plan_id", "annotation_type"),
    )
