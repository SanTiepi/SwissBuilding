"""BatiConnect - Memory Transfer model.

A transfer of building memory between parties or across lifecycle events.
When a building changes owner, manager, gets refinanced, or starts a new work cycle,
SwissBuilding is THE memory that transfers — verified, timestamped, with full chain of custody.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base
from app.models.mixins import ProvenanceMixin


class MemoryTransfer(Base, ProvenanceMixin):
    """A transfer of building memory between parties or across lifecycle events."""

    __tablename__ = "memory_transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # Transfer type
    # sale | refinance | management_change | work_cycle | insurance_renewal | regulatory_update | succession
    transfer_type = Column(String(50), nullable=False)
    transfer_label = Column(String(500), nullable=False)  # Libelle en francais

    # Parties
    from_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    to_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Status
    # initiated | memory_compiled | review_pending | accepted | contested | completed | cancelled
    status = Column(String(30), nullable=False, default="initiated")

    # Memory snapshot at transfer time
    memory_snapshot_id = Column(UUID(as_uuid=True), nullable=True)  # Points to BuildingSnapshot
    transfer_package_hash = Column(String(64), nullable=True)  # SHA-256 of complete memory

    # Content
    memory_sections = Column(JSON, nullable=True)
    # Sections: identity, diagnostics, interventions, obligations, procedures,
    # engagements, proof_chains, timeline, contradictions, unknowns, safe_to_start, grade

    sections_count = Column(Integer, default=0)
    documents_count = Column(Integer, default=0)
    engagements_count = Column(Integer, default=0)
    timeline_events_count = Column(Integer, default=0)

    # Verification
    integrity_verified = Column(Boolean, default=False)
    integrity_verified_at = Column(DateTime, nullable=True)

    # Acceptance
    accepted_at = Column(DateTime, nullable=True)
    accepted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acceptance_comment = Column(Text, nullable=True)

    # Contest
    contested_at = Column(DateTime, nullable=True)
    contested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    contest_comment = Column(Text, nullable=True)

    # Timestamps
    initiated_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_mem_transfer_building", "building_id"),
        Index("idx_mem_transfer_status", "status"),
        Index("idx_mem_transfer_type", "transfer_type"),
        Index("idx_mem_transfer_from_org", "from_org_id"),
        Index("idx_mem_transfer_to_org", "to_org_id"),
        Index("idx_mem_transfer_initiated", "initiated_at"),
    )
