"""BatiConnect — Procedure OS canonical grammar.

ProcedureTemplate: canonical procedure definition (e.g., SUVA notification, building permit VD).
ProcedureInstance: active procedure being executed for a building/case.

Procedures are native to BuildingCase (always linked via case_id).
Reuses existing FormTemplate for form bindings (link, don't duplicate).
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROCEDURE_TYPES = (
    "permit",
    "declaration",
    "notification",
    "authorization",
    "funding",
    "inspection",
    "certification",
    "transfer",
    "insurance",
    "other",
)

PROCEDURE_SCOPES = (
    "federal",
    "cantonal",
    "communal",
    "authority_body",
    "utility",
)

AUTHORITY_ROUTES = (
    "email",
    "portal",
    "physical",
    "api",
)

INSTANCE_STATUSES = (
    "not_started",
    "in_progress",
    "submitted",
    "complement_requested",
    "approved",
    "rejected",
    "expired",
    "cancelled",
)


class ProcedureTemplate(Base):
    """A canonical procedure template (e.g., asbestos remediation VD, building permit GE)."""

    __tablename__ = "procedure_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    procedure_type = Column(String(50), nullable=False)  # see PROCEDURE_TYPES
    scope = Column(String(30), nullable=False)  # see PROCEDURE_SCOPES
    canton = Column(String(10), nullable=True)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)

    # Steps — ordered list of procedure steps
    # [{"name": "diagnostic", "order": 1, "required": true, "description": "..."}, ...]
    steps = Column(JSON, nullable=True)

    # Required artifacts — what documents/evidence are needed
    # [{"type": "diagnostic_report", "description": "...", "mandatory": true}, ...]
    required_artifacts = Column(JSON, nullable=True)

    # Authority
    authority_name = Column(String(300), nullable=True)
    authority_route = Column(String(30), nullable=True)  # see AUTHORITY_ROUTES
    filing_channel = Column(String(300), nullable=True)  # how to submit

    # Forms — linked FormTemplate IDs
    form_template_ids = Column(JSON, nullable=True)

    # Work families this procedure applies to
    # ["asbestos_removal", "demolition", "renovation", ...]
    applicable_work_families = Column(JSON, nullable=True)

    # Timing
    typical_duration_days = Column(Integer, nullable=True)
    advance_notice_days = Column(Integer, nullable=True)  # how many days before works to file

    # Legal / metadata
    legal_basis = Column(String(500), nullable=True)  # e.g., "OTConst Art. 60a"
    source_url = Column(String(500), nullable=True)
    version = Column(String(20), default="1.0")
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction")
    instances = relationship("ProcedureInstance", back_populates="template")

    __table_args__ = (
        Index("idx_procedure_templates_type", "procedure_type"),
        Index("idx_procedure_templates_scope_canton", "scope", "canton"),
        Index("idx_procedure_templates_active", "active"),
    )


class ProcedureInstance(Base):
    """An active procedure being executed for a specific building/case."""

    __tablename__ = "procedure_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("procedure_templates.id"), nullable=False)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    status = Column(String(30), nullable=False, default="not_started")  # see INSTANCE_STATUSES

    # Step tracking
    current_step = Column(String(100), nullable=True)
    completed_steps = Column(JSON, nullable=True)  # [{"name": "...", "completed_at": "...", "completed_by": "..."}]

    # Artifacts collected
    collected_artifacts = Column(JSON, nullable=True)  # list of artifact/document IDs attached
    missing_artifacts = Column(JSON, nullable=True)  # what's still needed

    # Filing
    submitted_at = Column(DateTime, nullable=True)
    submission_reference = Column(String(255), nullable=True)
    authority_response = Column(Text, nullable=True)

    # Complement
    complement_requested_at = Column(DateTime, nullable=True)
    complement_details = Column(Text, nullable=True)

    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolution = Column(String(30), nullable=True)  # approved, rejected, expired

    # Blockers
    # [{"description": "...", "severity": "high", "since": "2026-01-01"}]
    blockers = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    template = relationship("ProcedureTemplate", back_populates="instances")
    building = relationship("Building")
    case = relationship("BuildingCase")
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("idx_procedure_instances_building_id", "building_id"),
        Index("idx_procedure_instances_case_id", "case_id"),
        Index("idx_procedure_instances_status", "status"),
        Index("idx_procedure_instances_template_id", "template_id"),
    )
