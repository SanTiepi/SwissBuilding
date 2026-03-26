"""BatiConnect - Ecosystem Engagement model.

A binding trace left by an ecosystem actor in SwissBuilding.
Generalizes the contractor_acknowledgment pattern into a universal engagement
system where ANY actor can leave a binding trace: seen, accepted, contested,
confirmed, reserved, refused, acknowledged, certified.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base
from app.models.mixins import ProvenanceMixin


class EcosystemEngagement(Base, ProvenanceMixin):
    """A binding trace left by an ecosystem actor in SwissBuilding."""

    __tablename__ = "ecosystem_engagements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # Who engaged
    actor_type = Column(
        String(50), nullable=False
    )  # diagnostician | contractor | property_manager | owner | insurer | authority | fiduciary
    actor_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(200), nullable=True)  # For external actors without account
    actor_email = Column(String(200), nullable=True)

    # What they engaged on
    subject_type = Column(
        String(50), nullable=False
    )  # diagnostic | document | pack | procedure | intervention | obligation | delivery | dossier | transfer
    subject_id = Column(UUID(as_uuid=True), nullable=False)
    subject_label = Column(String(500), nullable=True)  # Human-readable description

    # The engagement
    engagement_type = Column(
        String(30), nullable=False
    )  # seen | accepted | contested | confirmed | reserved | refused | acknowledged | certified
    status = Column(String(20), nullable=False, default="active")  # active | superseded | withdrawn

    # Content
    comment = Column(Text, nullable=True)  # Optional comment/reservation
    conditions = Column(JSON, nullable=True)  # Conditions attached to acceptance
    content_hash = Column(String(64), nullable=True)  # SHA-256 of the content at engagement time
    content_version = Column(Integer, nullable=True)  # Version of content at engagement time

    # Timestamps
    engaged_at = Column(DateTime, nullable=False, default=func.now())
    expires_at = Column(DateTime, nullable=True)  # Some engagements expire

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_eco_eng_building_id", "building_id"),
        Index("idx_eco_eng_actor", "actor_type", "actor_org_id"),
        Index("idx_eco_eng_subject", "subject_type", "subject_id"),
        Index("idx_eco_eng_type", "engagement_type"),
        Index("idx_eco_eng_status", "status"),
        Index("idx_eco_eng_engaged_at", "engaged_at"),
    )
