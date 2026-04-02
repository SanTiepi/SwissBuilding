"""Completeness Report — overall building dossier completeness snapshot."""

import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class CompletenessReport(Base):
    """Snapshot of overall completeness for a building dossier."""

    __tablename__ = "completeness_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    overall_score = Column(Float, nullable=False, default=0.0)  # 0-100
    dimension_scores = Column(JSON, nullable=True)  # {dimension: score}
    missing_items_count = Column(Integer, nullable=False, default=0)
    urgent_actions = Column(Integer, nullable=False, default=0)
    recommended_actions = Column(Integer, nullable=False, default=0)
    trend = Column(String(20), nullable=True)  # improving, stable, declining
    created_at = Column(DateTime, default=func.now(), nullable=False)
