import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingTrustScore(Base):
    __tablename__ = "building_trust_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # Score dimensions (0.0 to 1.0)
    overall_score = Column(Float, nullable=False)
    percent_proven = Column(Float, nullable=True)
    percent_inferred = Column(Float, nullable=True)
    percent_declared = Column(Float, nullable=True)
    percent_obsolete = Column(Float, nullable=True)
    percent_contradictory = Column(Float, nullable=True)

    # Counts
    total_data_points = Column(Integer, default=0)
    proven_count = Column(Integer, default=0)
    inferred_count = Column(Integer, default=0)
    declared_count = Column(Integer, default=0)
    obsolete_count = Column(Integer, default=0)
    contradictory_count = Column(Integer, default=0)

    # Trend
    trend = Column(String(20), nullable=True)
    previous_score = Column(Float, nullable=True)

    # Metadata
    assessed_at = Column(DateTime, default=func.now())
    assessed_by = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    building = relationship("Building")

    __table_args__ = (Index("idx_building_trust_scores_building_id", "building_id"),)
