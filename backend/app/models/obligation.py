"""BatiConnect — Obligation model for deadline/recurring obligation tracking."""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    obligation_type = Column(
        String(50), nullable=False
    )  # regulatory_inspection | insurance_renewal | contract_renewal | maintenance | authority_submission | diagnostic_followup | lease_milestone | custom
    due_date = Column(Date, nullable=False)
    recurrence = Column(
        String(30), nullable=True
    )  # monthly | quarterly | semi_annual | annual | biennial | five_yearly | null (one-time)
    status = Column(
        String(20), nullable=False, default="upcoming"
    )  # upcoming | due_soon | overdue | completed | cancelled
    priority = Column(String(10), nullable=False, default="medium")  # low | medium | high | critical
    responsible_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    responsible_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    linked_entity_type = Column(
        String(50), nullable=True
    )  # contract | lease | intervention | diagnostic | insurance_policy
    linked_entity_id = Column(UUID(as_uuid=True), nullable=True)
    reminder_days_before = Column(Integer, default=30)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    responsible_org = relationship("Organization", foreign_keys=[responsible_org_id])
    responsible_user = relationship("User", foreign_keys=[responsible_user_id])
    completed_by_user = relationship("User", foreign_keys=[completed_by_user_id])

    __table_args__ = (
        Index("idx_obligations_status", "status"),
        Index("idx_obligations_due_date", "due_date"),
        Index("idx_obligations_type", "obligation_type"),
    )
