"""
PreworkTrigger — persistent record of a pre-work diagnostic requirement.

Unlike the ephemeral triggers derived on-the-fly in readiness schemas,
these records track the full lifecycle of each trigger:
  pending → acknowledged → resolved | dismissed

Deterministic: synced from readiness evaluation, deduped by
(building_id, trigger_type). One active trigger per type per building.
"""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class PreworkTrigger(Base):
    __tablename__ = "prework_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # What
    trigger_type = Column(String(30), nullable=False)  # amiante_check, pcb_check, etc.
    reason = Column(Text, nullable=False)
    source_check = Column(String(60), nullable=False)  # readiness check_id that caused it
    legal_basis = Column(String(120), nullable=True)

    # Urgency & escalation
    urgency = Column(String(10), nullable=False, default="high")  # low, medium, high
    escalation_level = Column(Float, default=0.0)  # 0.0 = fresh, increases with age/severity

    # Lifecycle
    status = Column(String(20), nullable=False, default="pending")
    # pending → acknowledged → resolved | dismissed
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_reason = Column(Text, nullable=True)  # why it was resolved/dismissed

    # Provenance
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("readiness_assessments.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_prework_building_type", "building_id", "trigger_type"),
        Index("idx_prework_status", "status"),
    )
