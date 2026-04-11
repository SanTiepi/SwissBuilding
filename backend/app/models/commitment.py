"""BatiConnect — Commitment & Caveat models.

Commitments = promises, guarantees, undertakings, warranties tied to a building.
Caveats = explicit limitations, exclusions, warnings attached to packs/publications.

Both are first-class objects (not just text in pack output).
"""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class Commitment(Base):
    """A promise, guarantee, or undertaking related to a building."""

    __tablename__ = "commitments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    commitment_type = Column(
        String(50), nullable=False
    )  # guarantee | warranty | undertaking | promise | obligation | condition | reservation

    # Who committed to what
    committed_by_type = Column(String(30), nullable=False)  # contractor | owner | authority | insurer | seller | buyer
    committed_by_name = Column(String(200), nullable=False)
    committed_by_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Temporal
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    duration_months = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="active")  # active | expired | fulfilled | breached | withdrawn

    # Evidence
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    source_extraction_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    organization = relationship("Organization", foreign_keys=[organization_id])
    committed_by_org = relationship("Organization", foreign_keys=[committed_by_id])
    source_document = relationship("Document")

    __table_args__ = (
        Index("idx_commitments_building_id", "building_id"),
        Index("idx_commitments_status", "status"),
        Index("idx_commitments_type", "commitment_type"),
        Index("idx_commitments_building_status", "building_id", "status"),
        Index("idx_commitments_end_date", "end_date"),
    )


class Caveat(Base):
    """An explicit limitation, exclusion, or warning attached to a pack/publication."""

    __tablename__ = "caveats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)

    caveat_type = Column(String(50), nullable=False)  # authority_condition | contractor_exclusion | insurer_exclusion |
    # seller_caveat | lender_caveat | scope_limitation | temporal_limitation |
    # data_quality_warning | coverage_gap | unverified_claim

    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="info")  # info | warning | critical

    # What this caveat applies to
    applies_to_pack_types = Column(JSON, nullable=True)  # ["authority", "insurer", "transfer"]
    applies_to_audiences = Column(JSON, nullable=True)  # ["buyer", "insurer", "authority"]

    # Source
    source_type = Column(
        String(30), nullable=False, default="manual"
    )  # system_generated | manual | extraction | claim | decision
    source_id = Column(UUID(as_uuid=True), nullable=True)

    # Status
    active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")

    __table_args__ = (
        Index("idx_caveats_building_id", "building_id"),
        Index("idx_caveats_active", "active"),
        Index("idx_caveats_building_active", "building_id", "active"),
        Index("idx_caveats_type", "caveat_type"),
    )
