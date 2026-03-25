"""BatiConnect — Pilot Scorecard + Metric models for tracking pilot program outcomes."""

import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PilotScorecard(Base):
    __tablename__ = "pilot_scorecards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pilot_name = Column(String(200), nullable=False)
    pilot_code = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active | completed | stopped
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    target_buildings = Column(Integer, nullable=True)
    target_users = Column(Integer, nullable=True)
    exit_state = Column(String(20), nullable=True)  # promote | extend_narrowly | stop
    exit_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    metrics = relationship("PilotMetric", back_populates="scorecard", order_by="PilotMetric.measured_at")


class PilotMetric(Base):
    __tablename__ = "pilot_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scorecard_id = Column(UUID(as_uuid=True), ForeignKey("pilot_scorecards.id"), nullable=False, index=True)
    dimension = Column(
        String(50), nullable=False
    )  # recurring_usage | blocker_clarity | procedure_clarity | proof_reuse | actor_spread | trust_gained
    target_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    evidence_source = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    measured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    scorecard = relationship("PilotScorecard", back_populates="metrics")
