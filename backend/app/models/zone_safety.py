"""Zone-level safety readiness and occupant notices."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON

from app.database import Base


class ZoneSafetyStatus(Base):
    __tablename__ = "zone_safety_statuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False, index=True)
    building_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # Safety assessment
    safety_level = Column(String(30), nullable=False)  # safe, restricted, hazardous, closed
    restriction_type = Column(String(50), nullable=True)  # access_limited, ppe_required, evacuation, no_access
    hazard_types = Column(JSON, nullable=True)  # ["asbestos", "pcb", "lead"]
    # Context
    assessed_by = Column(UUID(as_uuid=True), nullable=True)
    assessment_notes = Column(Text, nullable=True)
    # Validity
    valid_from = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_zone_safety_zone_current", "zone_id", "is_current"),
        Index("idx_zone_safety_building", "building_id"),
    )


class OccupantNotice(Base):
    __tablename__ = "occupant_notices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), nullable=True)  # null = building-wide
    # Notice content
    notice_type = Column(String(50), nullable=False)  # safety_alert, access_restriction, work_schedule, clearance
    severity = Column(String(20), nullable=False)  # info, warning, critical
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    # Distribution
    audience = Column(String(50), nullable=False)  # all_occupants, floor_occupants, zone_occupants, management_only
    # State
    status = Column(String(30), default="draft")  # draft, published, expired, revoked
    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_occupant_notices_building", "building_id"),
        Index("idx_occupant_notices_building_status", "building_id", "status"),
    )
