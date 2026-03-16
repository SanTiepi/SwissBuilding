import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BuildingSnapshot(Base):
    __tablename__ = "building_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # When and why
    snapshot_type = Column(String(50), nullable=False)  # manual, diagnostic_completed, etc.
    trigger_event = Column(String(200), nullable=True)

    # Captured state (JSON blobs)
    passport_state_json = Column(JSON, nullable=True)
    trust_state_json = Column(JSON, nullable=True)
    readiness_state_json = Column(JSON, nullable=True)
    evidence_counts_json = Column(JSON, nullable=True)

    # Metadata
    passport_grade = Column(String(1), nullable=True)
    overall_trust = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)

    captured_at = Column(DateTime, default=func.now())
    captured_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    building = relationship("Building")
