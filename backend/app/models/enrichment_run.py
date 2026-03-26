"""BuildingEnrichmentRun — tracks each enrichment execution."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingEnrichmentRun(Base):
    __tablename__ = "building_enrichment_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True, index=True)
    address_input = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending|running|completed|failed
    sources_attempted = Column(Integer, default=0)
    sources_succeeded = Column(Integer, default=0)
    sources_failed = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    error_summary = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    building = relationship("Building", foreign_keys=[building_id])
    snapshots = relationship("BuildingSourceSnapshot", back_populates="enrichment_run", cascade="all, delete-orphan")
