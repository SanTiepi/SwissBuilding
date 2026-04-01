"""BatiConnect — BuildingCase: the unified operating episode root.

A bounded, time-limited engagement with a building.  Wraps and extends
existing entities (Intervention, TenderRequest, ComplianceArtefact, etc.)
without replacing them.

Case types: works, permit, authority_submission, tender, insurance_claim,
incident, maintenance, funding, transaction, due_diligence, transfer,
handoff, control, other.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CASE_TYPES = (
    "works",
    "permit",
    "authority_submission",
    "tender",
    "insurance_claim",
    "incident",
    "maintenance",
    "funding",
    "transaction",
    "due_diligence",
    "transfer",
    "handoff",
    "control",
    "other",
)

CASE_STATES = (
    "draft",
    "in_preparation",
    "ready",
    "in_progress",
    "blocked",
    "completed",
    "cancelled",
    "closed",
)

# Valid state transitions — from_state -> allowed target states
CASE_STATE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("in_preparation", "ready", "cancelled"),
    "in_preparation": ("ready", "blocked", "cancelled"),
    "ready": ("in_progress", "blocked", "cancelled"),
    "in_progress": ("blocked", "completed", "cancelled"),
    "blocked": ("in_preparation", "ready", "in_progress", "cancelled"),
    "completed": ("closed",),
    "cancelled": (),
    "closed": (),
}

CASE_PRIORITIES = ("low", "medium", "high", "critical")


class BuildingCase(Base):
    """The operating episode root.

    A bounded, time-limited engagement with a building — works, permits,
    tenders, authority submissions, insurance claims, incidents, maintenance
    programs, funding requests, transactions, due diligence, transfers, etc.
    """

    __tablename__ = "building_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    case_type = Column(String(50), nullable=False)  # see CASE_TYPES
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Lifecycle
    state = Column(String(30), nullable=False, default="draft")  # see CASE_STATES

    # Scope
    spatial_scope_ids = Column(JSON, nullable=True)  # zone UUIDs this case covers
    pollutant_scope = Column(JSON, nullable=True)  # ["asbestos", "pcb", ...]

    # Dates
    planned_start = Column(DateTime, nullable=True)
    planned_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)

    # Links to existing entities (optional — wraps, not replaces)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("interventions.id"), nullable=True)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tender_requests.id"), nullable=True)

    # Case steps / milestones (JSON array)
    # [{"name": "diagnostic", "status": "completed"}, {"name": "submission", "status": "pending"}]
    steps = Column(JSON, nullable=True)

    # Metadata
    canton = Column(String(10), nullable=True)
    authority = Column(String(255), nullable=True)
    priority = Column(String(20), default="medium")  # see CASE_PRIORITIES

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building")
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
    intervention = relationship("Intervention", foreign_keys=[intervention_id])
    tender = relationship("TenderRequest", foreign_keys=[tender_id])

    __table_args__ = (
        Index("idx_building_cases_building_id", "building_id"),
        Index("idx_building_cases_org_id", "organization_id"),
        Index("idx_building_cases_state", "state"),
        Index("idx_building_cases_case_type", "case_type"),
    )
