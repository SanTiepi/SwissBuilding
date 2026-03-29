"""Building Activity Ledger — tamper-evident multi-actor audit trail.

Every significant action on a building is recorded with WHO, WHAT, WHEN, WHY
and a SHA-256 hash chain for opposable proof.
"""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class BuildingActivity(Base):
    __tablename__ = "building_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # WHO — actor snapshot at time of action
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(50), nullable=False)
    actor_name = Column(String(200), nullable=False)

    # WHAT
    activity_type = Column(String(80), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # WHY
    reason = Column(Text, nullable=True)

    # Flexible payload
    metadata_json = Column(JSON, nullable=True)

    # Hash chain for tamper-evidence
    previous_hash = Column(String(64), nullable=True)
    activity_hash = Column(String(64), nullable=False)

    # WHEN
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_building_activity_building_created", "building_id", "created_at"),
        Index("idx_building_activity_actor", "actor_id"),
        Index("idx_building_activity_type", "activity_type"),
    )
