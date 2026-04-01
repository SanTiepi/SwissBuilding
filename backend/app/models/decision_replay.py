"""
BatiConnect - Decision Replay Model

A replayable snapshot of a decision and its basis.
Captures the ENTIRE basis at decision time (evidence, claims, trust, completeness, readiness)
then tracks what changed since to detect stale or invalidated decisions.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

REPLAY_STATUSES = ("current", "partially_stale", "stale", "invalidated")


class DecisionReplay(Base):
    """A replayable snapshot of a decision and its basis."""

    __tablename__ = "decision_replays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("building_decisions.id"), nullable=False)

    # Snapshot at decision time
    basis_snapshot = Column(JSON, nullable=True)  # evidence, claims, context at time of decision
    trust_state_at_decision = Column(JSON, nullable=True)  # trust scores at that time
    completeness_at_decision = Column(Float, nullable=True)
    readiness_at_decision = Column(JSON, nullable=True)

    # What changed since
    changes_since = Column(JSON, nullable=True)  # deltas/events since decision
    basis_still_valid = Column(Boolean, nullable=True)  # is the original basis still current
    invalidated_by = Column(JSON, nullable=True)  # what invalidated the basis

    # Assessment
    replay_status = Column(String(30), nullable=False, default="current")
    # current | partially_stale | stale | invalidated
    replay_summary = Column(Text, nullable=True)

    replayed_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    # Relationships
    building = relationship("Building")
    decision = relationship("BuildingDecision")

    __table_args__ = (
        Index("idx_decision_replays_building_id", "building_id"),
        Index("idx_decision_replays_decision_id", "decision_id"),
        Index("idx_decision_replays_replay_status", "replay_status"),
        Index("idx_decision_replays_building_status", "building_id", "replay_status"),
    )
