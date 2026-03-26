"""BuildingSourceSnapshot — raw + normalized data from each enrichment source."""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingSourceSnapshot(Base):
    __tablename__ = "building_source_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True, index=True)
    enrichment_run_id = Column(UUID(as_uuid=True), ForeignKey("building_enrichment_runs.id"), nullable=True, index=True)
    source_name = Column(String(100), nullable=False, index=True)
    source_category = Column(
        String(50), nullable=False
    )  # identity|environment|energy|transport|risk|social|regulatory|computed
    raw_data = Column(JSON, nullable=True)
    normalized_data = Column(JSON, nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    freshness_state = Column(String(20), nullable=False, default="current")  # current|aging|stale
    confidence = Column(String(20), nullable=False, default="medium")  # high|medium|low
    created_at = Column(DateTime(timezone=True), default=func.now())

    building = relationship("Building", foreign_keys=[building_id])
    enrichment_run = relationship("BuildingEnrichmentRun", back_populates="snapshots")
