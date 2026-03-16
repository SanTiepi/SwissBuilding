import uuid

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    intervention_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="completed")
    date_start = Column(Date, nullable=True)
    date_end = Column(Date, nullable=True)
    contractor_name = Column(String(255), nullable=True)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cost_chf = Column(Float, nullable=True)
    zones_affected = Column(JSON, nullable=True)
    materials_used = Column(JSON, nullable=True)
    diagnostic_id = Column(UUID(as_uuid=True), ForeignKey("diagnostics.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="interventions")
    diagnostic = relationship("Diagnostic")

    __table_args__ = (
        Index("idx_interventions_building_id", "building_id"),
        Index("idx_interventions_building_id_intervention_type", "building_id", "intervention_type"),
        Index("idx_interventions_status", "status"),
    )
