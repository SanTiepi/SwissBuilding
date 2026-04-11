"""BatiConnect — Exchange Contract models.

ExchangeContractVersion: versioned contracts for passport/pack publication formats.
PartnerExchangeContract: governance contracts bounding how partners interact with the system.
PartnerExchangeEvent: audit trail for partner exchange activity.
"""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ExchangeContractVersion(Base):
    __tablename__ = "exchange_contract_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_code = Column(
        String(50), nullable=False, index=True
    )  # diagnostic_report_v1 | authority_pack_v1 | building_passport_v1
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="draft")  # draft | active | deprecated | retired
    audience_type = Column(
        String(30), nullable=False
    )  # authority | insurer | lender | fiduciary | contractor | buyer | other
    payload_type = Column(
        String(50), nullable=False
    )  # diagnostic_report | authority_pack | transfer_package | passport_summary | building_dossier
    schema_reference = Column(String(500), nullable=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    compatibility_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class PartnerExchangeContract(Base):
    """Governs how a partner organization interacts with the system.

    Every partner interaction is bounded by a contract. Contracts define:
    - What operations a partner can perform
    - What data they can access and at what level
    - What trust level is required
    - What conformance profile applies to their submissions
    """

    __tablename__ = "partner_exchange_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    our_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)

    # Contract classification
    contract_type = Column(
        String(30), nullable=False
    )  # data_provider | data_consumer | bidirectional | submission_partner | exchange_partner

    # What the partner can do
    allowed_operations = Column(
        JSON, nullable=False, default=list
    )  # ["submit_diagnostics", "receive_packs", "acknowledge_transfers", "submit_quotes", "receive_assignments"]

    # API access governance
    api_access_level = Column(String(20), nullable=False, default="none")  # none | read_only | submit | full_partner
    allowed_endpoints = Column(JSON, nullable=True)  # explicit endpoint whitelist, null = use api_access_level defaults

    # Data governance
    data_sharing_scope = Column(
        String(20), nullable=False, default="none"
    )  # building_specific | case_specific | portfolio | none
    redaction_profile = Column(String(20), nullable=False, default="none")  # none | financial | personal | full

    # Trust requirements
    minimum_trust_level = Column(String(20), nullable=False, default="unknown")  # unknown | weak | adequate | strong

    # Conformance link
    conformance_profile_id = Column(UUID(as_uuid=True), ForeignKey("requirement_profiles.id"), nullable=True)

    # Lifecycle
    status = Column(String(20), nullable=False, default="draft")  # draft | active | suspended | terminated
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Terms
    terms_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    partner_org = relationship("Organization", foreign_keys=[partner_org_id])
    our_org = relationship("Organization", foreign_keys=[our_org_id])
    conformance_profile = relationship("RequirementProfile")
    exchange_events = relationship("PartnerExchangeEvent", back_populates="contract")

    __table_args__ = (
        Index("idx_pec_partner_org", "partner_org_id"),
        Index("idx_pec_our_org", "our_org_id"),
        Index("idx_pec_status", "status"),
        Index("idx_pec_contract_type", "contract_type"),
        Index("idx_pec_partner_status", "partner_org_id", "status"),
    )


class PartnerExchangeEvent(Base):
    """Audit trail for partner exchange activity within a contract."""

    __tablename__ = "partner_exchange_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("partner_exchange_contracts.id"), nullable=False, index=True)
    event_type = Column(
        String(50), nullable=False
    )  # access_granted | access_denied | submission_received | submission_validated | submission_rejected
    detail = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=func.now())

    contract = relationship("PartnerExchangeContract", back_populates="exchange_events")

    __table_args__ = (
        Index("idx_pee_contract_id", "contract_id"),
        Index("idx_pee_event_type", "event_type"),
        Index("idx_pee_recorded_at", "recorded_at"),
    )
