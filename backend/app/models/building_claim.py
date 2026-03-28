import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class BuildingClaim(Base):
    """An assertion about the building, case, or state. May be verified, contested, or superseded."""

    __tablename__ = "building_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # Who claims what
    claimed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    claim_type = Column(
        String(50), nullable=False
    )  # pollutant_presence | pollutant_absence | condition_assessment | risk_assessment |
    # compliance_status | scope_coverage | work_completion | material_identification | other
    subject = Column(String(500), nullable=False)  # what the claim is about
    assertion = Column(Text, nullable=False)  # the claim itself

    # Basis
    basis_type = Column(
        String(30), nullable=False
    )  # observation | diagnostic | document | inference | expert_judgment | ai_extraction
    basis_ids = Column(JSON, nullable=True)  # IDs of supporting evidence
    confidence = Column(Float, nullable=True)  # 0-1

    # Status
    status = Column(String(20), nullable=False, default="asserted")
    # asserted | verified | contested | superseded | withdrawn
    verified_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Contestation
    contested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    contestation_reason = Column(Text, nullable=True)

    # Supersession
    superseded_by_id = Column(UUID(as_uuid=True), ForeignKey("building_claims.id"), nullable=True)
    superseded_at = Column(DateTime, nullable=True)

    # Temporal validity
    observed_at = Column(DateTime, nullable=True, doc="When was this claim observed/established")
    effective_at = Column(DateTime, nullable=True, doc="When does this claim take effect")
    valid_from = Column(DateTime, nullable=True, doc="Start of claim validity window")
    valid_until = Column(DateTime, nullable=True, doc="End of claim validity window")
    stale_after = Column(DateTime, nullable=True, doc="When does this claim become unreliable")

    # Spatial scope
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("building_elements.id"), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    organization = relationship("Organization")
    claimed_by = relationship("User", foreign_keys=[claimed_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    contested_by = relationship("User", foreign_keys=[contested_by_id])
    superseded_by = relationship("BuildingClaim", remote_side=[id])
    zone = relationship("Zone")
    element = relationship("BuildingElement")

    __table_args__ = (
        Index("idx_building_claims_building_id", "building_id"),
        Index("idx_building_claims_status", "status"),
        Index("idx_building_claims_claim_type", "claim_type"),
        Index("idx_building_claims_building_status", "building_id", "status"),
    )


class BuildingDecision(Base):
    """A human or governed system-level choice recorded with authority."""

    __tablename__ = "building_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # Who decided what
    decision_maker_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    decision_type = Column(
        String(50), nullable=False
    )  # readiness_override | claim_resolution | contradiction_resolution |
    # tender_attribution | intervention_approval | permit_decision |
    # risk_acceptance | scope_change | priority_change | transfer_approval |
    # publication_approval | other

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Basis
    basis_claims = Column(JSON, nullable=True)  # claim IDs considered
    basis_evidence = Column(JSON, nullable=True)  # evidence IDs considered

    # Decision
    outcome = Column(String(500), nullable=False)  # the decision itself
    rationale = Column(Text, nullable=False)  # why this decision was made

    # Governance
    authority_level = Column(
        String(20), nullable=False, default="operator"
    )  # operator | manager | director | authority | system
    reversible = Column(Boolean, nullable=False, default=True)

    # Lifecycle
    status = Column(String(20), nullable=False, default="pending")
    # pending | enacted | reversed | superseded
    enacted_at = Column(DateTime, nullable=True)
    reversed_at = Column(DateTime, nullable=True)
    reversed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reversal_reason = Column(Text, nullable=True)

    # Temporal validity
    observed_at = Column(DateTime, nullable=True, doc="When was this decision observed/recorded")
    effective_at = Column(DateTime, nullable=True, doc="When does this decision take effect")
    valid_from = Column(DateTime, nullable=True, doc="Start of decision validity window")
    valid_until = Column(DateTime, nullable=True, doc="End of decision validity window")
    stale_after = Column(DateTime, nullable=True, doc="When does this decision become unreliable")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    organization = relationship("Organization")
    decision_maker = relationship("User", foreign_keys=[decision_maker_id])
    reversed_by = relationship("User", foreign_keys=[reversed_by_id])

    __table_args__ = (
        Index("idx_building_decisions_building_id", "building_id"),
        Index("idx_building_decisions_status", "status"),
        Index("idx_building_decisions_decision_type", "decision_type"),
        Index("idx_building_decisions_building_status", "building_id", "status"),
    )
