"""FreshnessWatch — tracks external changes that affect system truth.

Broader update intelligence layer: legal, procedural, portal, form,
dataset, and local-override changes.  When something changes externally,
the system must react concretely.
"""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# --- Allowed values (validated at schema layer) ---

DELTA_TYPES = (
    "new_rule",
    "amended_rule",
    "repealed_rule",
    "portal_change",
    "form_change",
    "procedure_change",
    "dataset_refresh",
    "schema_change",
    "local_override_change",
    "provider_breakage",
    "threshold_change",
)

SEVERITY_LEVELS = ("info", "warning", "critical")

STATUS_VALUES = ("detected", "under_review", "applied", "dismissed")


class FreshnessWatchEntry(Base):
    """Tracks external changes that affect the system's truth."""

    __tablename__ = "freshness_watch_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_registry_id = Column(UUID(as_uuid=True), ForeignKey("source_registry.id"), nullable=True)

    # What changed
    delta_type = Column(String(40), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Scope
    canton = Column(String(5), nullable=True)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)
    affected_work_families = Column(JSON, nullable=True)
    affected_procedure_types = Column(JSON, nullable=True)

    # Impact assessment
    severity = Column(String(10), nullable=False, default="info")
    affected_buildings_estimate = Column(Integer, nullable=True)

    # Required reactions (list of dicts)
    reactions = Column(JSON, nullable=True)

    # Resolution
    status = Column(String(20), nullable=False, default="detected")
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    dismiss_reason = Column(Text, nullable=True)

    # Source
    source_url = Column(String(500), nullable=True)
    detected_at = Column(DateTime(timezone=True), default=func.now())
    effective_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    source_registry = relationship("SourceRegistryEntry", foreign_keys=[source_registry_id])
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index("idx_fw_status", "status"),
        Index("idx_fw_severity", "severity"),
        Index("idx_fw_delta_type", "delta_type"),
        Index("idx_fw_canton", "canton"),
        Index("idx_fw_detected_at", "detected_at"),
    )
