"""Completeness Score — per-dimension dossier completeness for a building."""

import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class CompletenessScore(Base):
    """Tracks completeness score for a single dimension of a building dossier."""

    __tablename__ = "completeness_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    dimension = Column(String(64), nullable=False)  # building_metadata, energy_data, etc.
    score = Column(Float, nullable=False, default=0.0)  # 0-100
    missing_items = Column(JSON, nullable=True)  # [{field, importance}]
    required_actions = Column(JSON, nullable=True)  # [{action, priority, effort}]
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
