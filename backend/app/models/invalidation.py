"""InvalidationEvent — records when and why an artifact was invalidated.

Frontier Layer #7: Invalidation Engine.
Tracks all invalidation triggers and their required reactions.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base

# Allowed values (validated at schema layer)
TRIGGER_TYPES = (
    "source_refresh",
    "rule_change",
    "form_change",
    "document_arrival",
    "contradiction",
    "post_works_update",
    "transfer",
    "new_evidence",
    "temporal_expiry",
    "manual",
)

AFFECTED_TYPES = (
    "pack",
    "passport",
    "form_template",
    "form_instance",
    "safe_to_x_state",
    "publication",
    "claim",
    "procedure_step",
)

SEVERITY_LEVELS = ("info", "warning", "critical")

REQUIRED_REACTIONS = (
    "review_required",
    "republish",
    "reopen_case",
    "refresh_safe_to_x",
    "update_template",
    "supersede",
    "notify_only",
)

STATUS_VALUES = ("detected", "acknowledged", "resolved", "ignored")


class InvalidationEvent(Base):
    """Records when and why an artifact was invalidated."""

    __tablename__ = "invalidation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # Trigger
    trigger_type = Column(String(30), nullable=False)
    trigger_id = Column(UUID(as_uuid=True), nullable=True)
    trigger_description = Column(String(500), nullable=False)

    # What was invalidated
    affected_type = Column(String(30), nullable=False)
    affected_id = Column(UUID(as_uuid=True), nullable=False)

    # Impact
    impact_reason = Column(Text, nullable=False)
    severity = Column(String(10), nullable=False, default="warning")

    # Required reaction
    required_reaction = Column(String(30), nullable=False, default="review_required")

    # Resolution
    status = Column(String(20), nullable=False, default="detected")
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_note = Column(Text, nullable=True)

    detected_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_invalidation_building_id", "building_id"),
        Index("idx_invalidation_status", "status"),
        Index("idx_invalidation_severity", "severity"),
        Index("idx_invalidation_affected", "affected_type", "affected_id"),
        Index("idx_invalidation_detected_at", "detected_at"),
    )
