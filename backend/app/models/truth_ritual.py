import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class TruthRitual(Base):
    """A governed act that changes the truth status of an artifact or building state.

    Every ritual is traceable: who, when, what, why.
    8 ritual types: validate, freeze, publish, transfer, acknowledge, reopen, supersede, receipt.
    """

    __tablename__ = "truth_rituals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)

    # What ritual
    ritual_type = Column(String(30), nullable=False)
    # Types: validate, freeze, publish, transfer, acknowledge, reopen, supersede, receipt

    # Who
    performed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # What artifact/object
    target_type = Column(String(50), nullable=False)
    # evidence, claim, decision, publication, document, extraction, pack, passport, case
    target_id = Column(UUID(as_uuid=True), nullable=False)

    # Why
    reason = Column(Text, nullable=True)

    # Context
    case_id = Column(UUID(as_uuid=True), nullable=True)

    # Provenance
    content_hash = Column(String(64), nullable=True)  # SHA-256 of the artifact at time of ritual
    version = Column(Integer, nullable=True)

    # For transfer/publish rituals
    recipient_type = Column(String(30), nullable=True)  # authority, owner, insurer, contractor, notary
    recipient_id = Column(UUID(as_uuid=True), nullable=True)
    delivery_method = Column(String(30), nullable=True)  # in_app, email, download, api

    # For acknowledge/receipt rituals
    acknowledged_by_id = Column(UUID(as_uuid=True), nullable=True)
    receipt_hash = Column(String(64), nullable=True)  # proof of receipt

    # For supersede rituals
    supersedes_id = Column(UUID(as_uuid=True), nullable=True)  # ID of the artifact being superseded

    # For reopen rituals
    reopen_reason = Column(Text, nullable=True)

    performed_at = Column(DateTime, default=func.now())

    # Temporal validity
    observed_at = Column(DateTime, nullable=True, doc="When was the ritual observed/recorded")
    effective_at = Column(DateTime, nullable=True, doc="When does this ritual take effect")
    valid_from = Column(DateTime, nullable=True, doc="Start of ritual effect validity window")
    valid_until = Column(DateTime, nullable=True, doc="End of ritual effect validity window")
    stale_after = Column(DateTime, nullable=True, doc="When does this ritual record become unreliable")

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_truth_ritual_building_id", "building_id"),
        Index("idx_truth_ritual_type", "ritual_type"),
        Index("idx_truth_ritual_target", "target_type", "target_id"),
        Index("idx_truth_ritual_performed_by", "performed_by_id"),
        Index("idx_truth_ritual_performed_at", "performed_at"),
    )
