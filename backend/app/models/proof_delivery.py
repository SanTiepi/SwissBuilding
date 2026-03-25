"""BatiConnect - Proof Delivery tracking model.

Tracks delivery of documents, packs, and authority artefacts
to external audiences with full lifecycle (queued → sent → delivered → viewed → acknowledged).
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class ProofDelivery(Base, ProvenanceMixin):
    __tablename__ = "proof_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # What was delivered
    target_type = Column(
        String(50), nullable=False
    )  # document | pack | authority_pack | transfer_package | diagnostic_publication
    target_id = Column(UUID(as_uuid=True), nullable=False)

    # Who received it
    audience = Column(
        String(30), nullable=False
    )  # owner | authority | insurer | lender | fiduciary | contractor | other
    recipient_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    recipient_email = Column(String(200), nullable=True)

    # How it was delivered
    delivery_method = Column(String(20), nullable=False)  # email | download | api | postal | handoff

    # Lifecycle
    status = Column(
        String(20), nullable=False, default="queued"
    )  # queued | sent | delivered | viewed | acknowledged | failed
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    # Integrity
    content_hash = Column(String(64), nullable=True)  # SHA-256 at send time
    content_version = Column(Integer, nullable=True)

    # Error / notes
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_proof_deliveries_building_id", "building_id"),
        Index("idx_proof_deliveries_target", "target_type", "target_id"),
        Index("idx_proof_deliveries_status", "status"),
        Index("idx_proof_deliveries_audience", "audience"),
    )
