"""BatiConnect — Programme I: AIMetrics — aggregated AI accuracy tracking."""

import uuid

from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class AIMetrics(Base):
    __tablename__ = "ai_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)  # diagnostic | material | sample
    field_name = Column(String(100), nullable=False)  # e.g. "material_type", "hazard_level"
    total_extractions = Column(Integer, default=0)
    total_corrections = Column(Integer, default=0)
    error_rate = Column(Float, default=0.0)  # corrections / total_extractions
    common_errors = Column(JSON, default=list)  # [{original, corrected, count}]
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_ai_metrics_entity_field", "entity_type", "field_name", unique=True),
    )
