"""BatiConnect — Mise en concurrence encadree: RFQ models.

Provides the intelligence layer on top of the marketplace RFQ primitives:
- TenderRequest: auto-generated RFQ from building dossier data
- TenderInvitation: invitation sent to a contractor org for a specific tender
- TenderQuote: quote received with optional PDF extraction
- TenderComparison: persisted neutral comparison of quotes
"""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# ---------------------------------------------------------------------------
# Work type constants
# ---------------------------------------------------------------------------
TENDER_WORK_TYPES = (
    "asbestos_removal",
    "pcb_removal",
    "lead_removal",
    "hap_removal",
    "radon_mitigation",
    "pfas_remediation",
    "multi_pollutant",
    "other",
)

TENDER_STATUSES = ("draft", "sent", "collecting", "closed", "attributed", "cancelled")

INVITATION_STATUSES = ("pending", "viewed", "accepted", "declined", "expired")

QUOTE_STATUSES = ("received", "under_review", "selected", "rejected")


class TenderRequest(Base):
    """A request for quotes generated from a building dossier.

    Unlike ClientRequest (marketplace), TenderRequest is auto-generated from
    passport data with scope_summary, auto-attached documents, and dossier
    intelligence baked in.
    """

    __tablename__ = "tender_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    scope_summary = Column(Text, nullable=True)  # auto-generated from building data

    work_type = Column(String(50), nullable=False)  # see TENDER_WORK_TYPES
    deadline_submission = Column(DateTime, nullable=True)
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)

    status = Column(String(20), nullable=False, default="draft")  # see TENDER_STATUSES

    attachments_auto = Column(JSON, nullable=True)  # list of auto-attached document/diagnostic IDs
    attachments_manual = Column(JSON, nullable=True)  # list of manually added document IDs

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building")
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
    invitations = relationship("TenderInvitation", back_populates="tender")
    quotes = relationship("TenderQuote", back_populates="tender")
    comparisons = relationship("TenderComparison", back_populates="tender")


class TenderInvitation(Base):
    """An invitation sent to a contractor organization for a specific tender."""

    __tablename__ = "tender_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tender_requests.id"), nullable=False, index=True)
    contractor_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)

    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)

    status = Column(String(20), nullable=False, default="pending")  # see INVITATION_STATUSES
    access_token = Column(String(128), unique=True, nullable=True)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    tender = relationship("TenderRequest", back_populates="invitations")
    contractor_org = relationship("Organization", foreign_keys=[contractor_org_id])


class TenderQuote(Base):
    """A quote received from a contractor for a tender."""

    __tablename__ = "tender_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tender_requests.id"), nullable=False, index=True)
    invitation_id = Column(UUID(as_uuid=True), ForeignKey("tender_invitations.id"), nullable=True)
    contractor_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)

    total_amount_chf = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="CHF")
    scope_description = Column(Text, nullable=True)
    exclusions = Column(Text, nullable=True)
    inclusions = Column(Text, nullable=True)
    estimated_duration_days = Column(Integer, nullable=True)
    validity_date = Column(Date, nullable=True)

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    extracted_data = Column(JSON, nullable=True)  # structured extraction from PDF

    status = Column(String(20), nullable=False, default="received")  # see QUOTE_STATUSES
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    tender = relationship("TenderRequest", back_populates="quotes")
    invitation = relationship("TenderInvitation")
    contractor_org = relationship("Organization", foreign_keys=[contractor_org_id])
    document = relationship("Document")


class TenderComparison(Base):
    """A saved comparison view of quotes for a tender.

    Stores a normalized, neutral comparison matrix.
    No ranking, no recommendation — just facts.
    """

    __tablename__ = "tender_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tender_requests.id"), nullable=False, index=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    comparison_data = Column(JSON, nullable=True)  # normalized comparison matrix
    selected_quote_id = Column(UUID(as_uuid=True), ForeignKey("tender_quotes.id"), nullable=True)
    selection_reason = Column(Text, nullable=True)
    attributed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    tender = relationship("TenderRequest", back_populates="comparisons")
    created_by = relationship("User", foreign_keys=[created_by_id])
    selected_quote = relationship("TenderQuote")
