"""BatiConnect — PermitStep model for individual steps within a permit procedure."""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class PermitStep(Base):
    __tablename__ = "permit_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    procedure_id = Column(UUID(as_uuid=True), ForeignKey("permit_procedures.id"), nullable=False, index=True)
    step_type = Column(
        String(30), nullable=False
    )  # submission | review | complement_request | complement_response | decision | acknowledgement
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | active | completed | skipped | blocked
    assigned_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    required_documents = Column(JSON, nullable=True)  # [{document_id, label, required: bool}]
    compliance_artefact_id = Column(UUID(as_uuid=True), ForeignKey("compliance_artefacts.id"), nullable=True)
    notes = Column(Text, nullable=True)
    step_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    procedure = relationship("PermitProcedure", back_populates="steps")
    assigned_org = relationship("Organization", foreign_keys=[assigned_org_id])
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])

    __table_args__ = (
        Index("idx_permit_steps_status", "status"),
        Index("idx_permit_steps_order", "procedure_id", "step_order"),
    )
