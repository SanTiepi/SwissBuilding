"""BatiConnect — PermitProcedure model for authority permit workflow tracking."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class PermitProcedure(ProvenanceMixin, Base):
    __tablename__ = "permit_procedures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    procedure_type = Column(
        String(50), nullable=False
    )  # construction_permit | demolition_permit | suva_notification | cantonal_declaration | communal_authorization | other
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    authority_name = Column(String(200), nullable=True)
    authority_type = Column(String(50), nullable=True)
    status = Column(
        String(30), nullable=False, default="draft"
    )  # draft | submitted | under_review | complement_requested | approved | rejected | expired | withdrawn
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    reference_number = Column(String(100), nullable=True)
    assigned_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    assigned_org = relationship("Organization", foreign_keys=[assigned_org_id])
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    steps = relationship("PermitStep", back_populates="procedure", order_by="PermitStep.step_order")
    authority_requests = relationship("AuthorityRequest", back_populates="procedure")

    __table_args__ = (
        Index("idx_permit_procedures_status", "status"),
        Index("idx_permit_procedures_type", "procedure_type"),
    )
