"""SourceRegistryEntry + SourceHealthEvent — registry of all data sources and their health."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SourceRegistryEntry(Base):
    """Registry of all data sources used by the system."""

    __tablename__ = "source_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identity
    name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    family = Column(String, nullable=False)
    # identity, spatial, constraint, procedure, standard, commercial, partner, live, document
    circle = Column(Integer, nullable=False)  # 1, 2, 3
    source_class = Column(String, nullable=False)
    # official, observed, commercial, partner_fed, derived

    # Access
    access_mode = Column(String, nullable=False)
    # api, bulk, file, portal, partner, watch_only
    base_url = Column(String, nullable=True)

    # Freshness
    freshness_policy = Column(String, default="on_demand")
    # real_time, daily, weekly, monthly, quarterly, event_driven, on_demand
    cache_ttl_hours = Column(Integer, nullable=True)

    # Trust
    trust_posture = Column(String, nullable=False)
    # canonical_identity, canonical_constraint, observed_context, supporting_evidence,
    # commercial_hint, derived_only

    # Coverage
    geographic_scope = Column(String, default="switzerland")
    canton_scope = Column(JSON, nullable=True)  # ["VD", "GE", "FR"] or null for national

    # Workspace consumers
    workspace_consumers = Column(JSON, nullable=True)
    # ["building_home", "case_room", "safe_to_x", "passport", "finance", "portfolio"]

    # Status
    status = Column(String, default="active")
    # active, degraded, unavailable, deprecated, planned

    # Metadata
    license_notes = Column(Text, nullable=True)
    fallback_source_name = Column(String, nullable=True)
    priority = Column(String, default="now")  # now, next, later, partner_gated

    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    health_events = relationship("SourceHealthEvent", back_populates="source", lazy="selectin")


class SourceHealthEvent(Base):
    """Health events for source monitoring. Append-only audit trail."""

    __tablename__ = "source_health_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("source_registry.id"), nullable=False, index=True)

    event_type = Column(String, nullable=False)
    # healthy, degraded, unavailable, schema_drift, timeout, error, recovered, fallback_used

    description = Column(Text, nullable=True)
    error_detail = Column(Text, nullable=True)

    # Impact
    affected_buildings_count = Column(Integer, nullable=True)
    fallback_used = Column(Boolean, default=False)
    fallback_source_name = Column(String, nullable=True)

    detected_at = Column(DateTime(timezone=True), default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    source = relationship("SourceRegistryEntry", back_populates="health_events")
