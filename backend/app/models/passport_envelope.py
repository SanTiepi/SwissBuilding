"""Building Passport Envelope — sovereign, versioned, receipted, transferable."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class BuildingPassportEnvelope(Base):
    """A sovereign, versioned, receipted, role-redactable, transferable building passport."""

    __tablename__ = "building_passport_envelopes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Version
    version = Column(Integer, nullable=False, default=1)
    version_label = Column(String(255), nullable=True)

    # Content
    passport_data = Column(JSON, nullable=False)
    sections_included = Column(JSON, nullable=False)

    # Integrity
    content_hash = Column(String(64), nullable=False)

    # Redaction
    redaction_profile = Column(String(50), nullable=True)
    financials_redacted = Column(Boolean, default=False)
    personal_data_redacted = Column(Boolean, default=False)

    # Transfer sovereignty
    is_sovereign = Column(Boolean, default=True)
    supersedes_id = Column(UUID(as_uuid=True), ForeignKey("building_passport_envelopes.id"), nullable=True)
    superseded_at = Column(DateTime, nullable=True)

    # Temporal validity
    observed_at = Column(DateTime, nullable=True, doc="When was this passport snapshot taken")
    effective_at = Column(DateTime, nullable=True, doc="When does this passport take effect")
    valid_from = Column(DateTime, nullable=True, doc="Start of passport validity window")
    valid_until = Column(DateTime, nullable=True, doc="End of passport validity window")
    stale_after = Column(DateTime, nullable=True, doc="When does this passport become unreliable")

    # Lifecycle: draft, frozen, published, transferred, acknowledged, superseded, archived
    status = Column(String(30), nullable=False, default="draft")

    frozen_at = Column(DateTime, nullable=True)
    frozen_by_id = Column(UUID(as_uuid=True), nullable=True)

    published_at = Column(DateTime, nullable=True)
    published_by_id = Column(UUID(as_uuid=True), nullable=True)

    # Transfer tracking
    transferred_to_type = Column(String(50), nullable=True)
    transferred_to_id = Column(UUID(as_uuid=True), nullable=True)
    transferred_at = Column(DateTime, nullable=True)
    transfer_method = Column(String(30), nullable=True)

    # Receipt
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by_id = Column(UUID(as_uuid=True), nullable=True)
    receipt_hash = Column(String(64), nullable=True)

    # Re-import capability
    reimportable = Column(Boolean, default=True)
    reimport_format = Column(String(20), default="json")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_passport_envelope_building_id", "building_id"),
        Index("idx_passport_envelope_org_id", "organization_id"),
        Index("idx_passport_envelope_status", "status"),
        Index("idx_passport_envelope_sovereign", "building_id", "is_sovereign"),
    )


class PassportTransferReceipt(Base):
    """Proof of passport delivery and acknowledgment."""

    __tablename__ = "passport_transfer_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envelope_id = Column(UUID(as_uuid=True), ForeignKey("building_passport_envelopes.id"), nullable=False)
    sender_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    recipient_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    recipient_name = Column(String(255), nullable=True)

    sent_at = Column(DateTime, nullable=False)
    delivery_method = Column(String(30), nullable=False)
    delivery_proof_hash = Column(String(64), nullable=False)

    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by_name = Column(String(255), nullable=True)
    receipt_hash = Column(String(64), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_transfer_receipt_envelope_id", "envelope_id"),
        Index("idx_transfer_receipt_sender_org", "sender_org_id"),
    )
