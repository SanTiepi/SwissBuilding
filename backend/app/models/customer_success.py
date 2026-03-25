"""BatiConnect — Customer Success Milestone model.

Tracks key adoption milestones per organization, grounded in real product events.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class CustomerSuccessMilestone(Base):
    __tablename__ = "customer_success_milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    milestone_type = Column(
        String(50), nullable=False
    )  # first_workflow_win | first_proof_reuse | first_actor_spread | first_blocker_caught | first_trusted_pack | first_exchange_publication
    status = Column(String(20), nullable=False, default="pending")  # pending | achieved | blocked
    achieved_at = Column(DateTime, nullable=True)
    evidence_entity_type = Column(String(50), nullable=True)
    evidence_entity_id = Column(UUID(as_uuid=True), nullable=True)
    evidence_summary = Column(String(500), nullable=True)
    blocker_description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_cs_milestone_org_type", "organization_id", "milestone_type"),
        Index("idx_cs_milestone_status", "status"),
    )
