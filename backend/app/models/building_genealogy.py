"""
BatiConnect - Building Genealogy Models

Three first-class genealogy types that formalize a building's history:
- TransformationEpisode: a significant transformation (construction, renovation, remediation, etc.)
- OwnershipEpisode: a period of ownership
- HistoricalClaim: a historical assertion that may not be currently verifiable
"""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TransformationEpisode(Base):
    """A significant transformation in the building's history."""

    __tablename__ = "transformation_episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    episode_type = Column(
        String(30),
        nullable=False,
    )  # construction, renovation, extension, demolition_partial, change_of_use, merger, split, restoration, modernization, remediation, other

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Temporal
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    approximate = Column(Boolean, default=False, nullable=False)

    # Evidence
    evidence_basis = Column(
        String(30),
        nullable=False,
        default="unknown",
    )  # documented, observed, inferred, declared, unknown
    evidence_ids = Column(JSON, nullable=True)  # linked evidence/document IDs

    # Scope
    spatial_scope = Column(JSON, nullable=True)  # affected zones/elements

    # Comparison
    state_before_summary = Column(Text, nullable=True)
    state_after_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", backref="transformation_episodes")

    __table_args__ = (Index("idx_transformation_episodes_building_period", "building_id", "period_start"),)


class OwnershipEpisode(Base):
    """A period of ownership in the building's history."""

    __tablename__ = "ownership_episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    owner_name = Column(String(500), nullable=True)
    owner_type = Column(
        String(30),
        nullable=False,
        default="unknown",
    )  # individual, company, public, cooperative, foundation, unknown

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    approximate = Column(Boolean, default=False, nullable=False)

    # Evidence
    evidence_basis = Column(
        String(30),
        nullable=False,
        default="declared",
    )  # registry, document, declared, inferred
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    # Transfer
    acquisition_type = Column(
        String(30),
        nullable=False,
        default="unknown",
    )  # purchase, inheritance, donation, exchange, other, unknown

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", backref="ownership_episodes")
    source_document = relationship("Document", foreign_keys=[source_document_id])

    __table_args__ = (Index("idx_ownership_episodes_building_period", "building_id", "period_start"),)


class HistoricalClaim(Base):
    """A historical assertion about the building that may not be currently verifiable."""

    __tablename__ = "historical_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    claim_type = Column(
        String(30),
        nullable=False,
    )  # construction_date, material_presence, use_type, intervention_performed, condition_at_date, owner_at_date, other

    subject = Column(String(500), nullable=False)
    assertion = Column(String(1000), nullable=False)

    reference_date = Column(Date, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    evidence_basis = Column(
        String(30),
        nullable=False,
        default="inference",
    )  # document, photograph, testimony, inference, registry
    confidence = Column(Float, nullable=False, default=0.5)
    source_description = Column(String(1000), nullable=True)

    # Status
    status = Column(
        String(20),
        nullable=False,
        default="recorded",
    )  # recorded, verified, contested, superseded

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", backref="historical_claims")

    __table_args__ = (Index("idx_historical_claims_building_type", "building_id", "claim_type"),)
