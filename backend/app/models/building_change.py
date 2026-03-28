"""
BatiConnect - Building Change Grammar Models

Four first-class change types that formalize how a building evolves:
- Observation: a point-in-time reading or measurement
- Event: a significant occurrence that alters building state
- Delta: a computed difference between two states
- Signal: a pattern or anomaly detected from observations/events/deltas
"""

import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingObservation(Base):
    """A point-in-time reading or measurement about the building."""

    __tablename__ = "building_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), nullable=True)

    observation_type = Column(String(30), nullable=False)  # measurement, inspection, assessment, reading, survey
    observer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    observer_role = Column(String(30), nullable=False)  # diagnostician, owner, contractor, authority, system
    observed_at = Column(DateTime, nullable=False, default=func.now())

    # What was observed
    target_type = Column(String(30), nullable=False)  # zone, element, material, system, building
    target_id = Column(UUID(as_uuid=True), nullable=True)
    subject = Column(String(255), nullable=False)  # "asbestos presence", "radon level"
    value = Column(String(500), nullable=False)  # the observed value
    unit = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)  # 0-1
    method = Column(
        String(30), nullable=False, default="visual"
    )  # visual, laboratory, instrument, document_review, ai_extraction

    # Provenance
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    source_extraction_id = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Temporal validity (observed_at already defined above)
    effective_at = Column(DateTime, nullable=True, doc="When does this observation take effect")
    valid_from = Column(DateTime, nullable=True, doc="Start of observation validity window")
    valid_until = Column(DateTime, nullable=True, doc="End of observation validity window")
    stale_after = Column(DateTime, nullable=True, doc="When does this observation become unreliable")

    created_at = Column(DateTime, default=func.now())

    building = relationship("Building", backref="building_observations")
    observer = relationship("User", foreign_keys=[observer_id])
    source_document = relationship("Document", foreign_keys=[source_document_id])


class BuildingEvent(Base):
    """A significant occurrence that alters building state."""

    __tablename__ = "building_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), nullable=True)

    event_type = Column(
        String(50), nullable=False
    )  # intervention_started, intervention_completed, diagnostic_received, etc.

    occurred_at = Column(DateTime, nullable=False, default=func.now())
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Impact
    impact_scope = Column(String(30), nullable=True)  # building, zone, element, case, document
    impact_target_id = Column(UUID(as_uuid=True), nullable=True)
    impact_description = Column(String(500), nullable=True)
    severity = Column(String(20), nullable=False, default="info")  # info, minor, significant, critical

    # Links
    source_type = Column(String(50), nullable=True)  # intervention, diagnostic, document, case, etc.
    source_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, default=func.now())

    building = relationship("Building", backref="building_change_events")
    actor = relationship("User", foreign_keys=[actor_id])


class BuildingDelta(Base):
    """A computed difference between two states of the building."""

    __tablename__ = "building_deltas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    delta_type = Column(
        String(50), nullable=False
    )  # completeness_change, trust_change, grade_change, readiness_change, etc.

    computed_at = Column(DateTime, nullable=False, default=func.now())
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Before/after
    before_value = Column(String(500), nullable=False)
    after_value = Column(String(500), nullable=False)
    before_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("building_snapshots.id"), nullable=True)
    after_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("building_snapshots.id"), nullable=True)

    # Interpretation
    direction = Column(String(20), nullable=False)  # improved, degraded, unchanged, mixed
    magnitude = Column(String(20), nullable=False, default="minor")  # minor, moderate, major
    explanation = Column(Text, nullable=True)

    # Trigger
    triggered_by_event_id = Column(UUID(as_uuid=True), ForeignKey("building_events.id"), nullable=True)

    created_at = Column(DateTime, default=func.now())

    building = relationship("Building", backref="building_deltas")
    before_snapshot = relationship("BuildingSnapshot", foreign_keys=[before_snapshot_id])
    after_snapshot = relationship("BuildingSnapshot", foreign_keys=[after_snapshot_id])
    triggered_by_event = relationship("BuildingEvent", foreign_keys=[triggered_by_event_id])


class BuildingSignal(Base):
    """A pattern or anomaly detected from observations, events, or deltas."""

    __tablename__ = "building_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    signal_type = Column(
        String(50), nullable=False
    )  # expiration_approaching, contradiction_detected, coverage_gap, etc.

    detected_at = Column(DateTime, nullable=False, default=func.now())
    severity = Column(String(20), nullable=False, default="info")  # info, warning, critical
    confidence = Column(Float, nullable=True)  # 0-1

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    recommended_action = Column(String(500), nullable=True)

    # Basis
    based_on_type = Column(String(20), nullable=False)  # observation, event, delta, multiple
    based_on_ids = Column(JSON, nullable=True)  # list of IDs that triggered this signal

    # Resolution
    status = Column(String(20), nullable=False, default="active")  # active, acknowledged, resolved, dismissed
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", backref="building_signals")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
