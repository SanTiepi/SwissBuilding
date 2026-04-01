"""
BatiConnect - Unknowns Ledger Model

First-class tracking of what is unknown about a building.
Unknowns are not just diagnostics -- they include missing documents,
unverified claims, spatial gaps, stale evidence, contradicted facts,
coverage holes, missing obligation proofs, and unresolved questions.

Every unknown shows its impact (what it blocks) and risk acceptance
requires a note (never silent).
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# ---------------------------------------------------------------------------
# Type / status constants (validation at schema layer)
# ---------------------------------------------------------------------------

UNKNOWN_ENTRY_TYPES = (
    "missing_diagnostic",
    "expired_diagnostic",
    "missing_document",
    "unverified_claim",
    "spatial_gap",
    "scope_gap",
    "stale_evidence",
    "contradicted_fact",
    "missing_obligation_proof",
    "coverage_gap",
    "unresolved_question",
    "missing_party_data",
)

UNKNOWN_ENTRY_SEVERITIES = ("critical", "high", "medium", "low")

UNKNOWN_ENTRY_STATUSES = (
    "open",
    "investigating",
    "resolved",
    "accepted_risk",
    "deferred",
)

RESOLUTION_METHODS = (
    "new_evidence",
    "diagnostic_ordered",
    "claim_verified",
    "risk_accepted",
    "auto_resolved",
)

EFFORT_LEVELS = ("quick", "moderate", "heavy", "partner_required")

SOURCE_TYPES = (
    "completeness_engine",
    "unknown_generator",
    "predictive_readiness",
    "manual",
)


class UnknownEntry(Base):
    """First-class tracking of what is unknown about a building."""

    __tablename__ = "unknown_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), nullable=True)

    # What is unknown
    unknown_type = Column(String(50), nullable=False)
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Spatial scope
    zone_id = Column(UUID(as_uuid=True), nullable=True)
    element_id = Column(UUID(as_uuid=True), nullable=True)

    # Severity
    severity = Column(String(20), default="medium")

    # Impact
    blocks_safe_to_x = Column(JSON, nullable=True)  # ["start", "sell", "insure"]
    blocks_pack_types = Column(JSON, nullable=True)  # ["authority", "insurer"]

    # Risk assessment
    risk_of_acting = Column(Text, nullable=True)
    estimated_resolution_effort = Column(String(30), nullable=True)

    # Resolution
    status = Column(String(20), default="open")
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_method = Column(String(30), nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Provenance
    detected_by = Column(String(30), default="system")
    source_type = Column(String(30), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building")
    resolved_by_user = relationship("User", foreign_keys=[resolved_by_id])

    __table_args__ = (
        Index("idx_unknown_entries_building_id", "building_id"),
        Index("idx_unknown_entries_status", "status"),
        Index("idx_unknown_entries_building_status", "building_id", "status"),
    )
