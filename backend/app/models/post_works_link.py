"""BatiConnect — Lot 4: PostWorksLink — closed-loop post-works truth."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class PostWorksLink(Base):
    __tablename__ = "post_works_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    completion_confirmation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("completion_confirmations.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    intervention_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interventions.id"),
        nullable=False,
        index=True,
    )
    before_snapshot_id = Column(UUID(as_uuid=True), nullable=True)
    after_snapshot_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    grade_delta = Column(JSON, nullable=True)
    trust_delta = Column(JSON, nullable=True)
    completeness_delta = Column(JSON, nullable=True)
    residual_risks = Column(JSON, nullable=True)
    drafted_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    completion_confirmation = relationship("CompletionConfirmation")
    intervention = relationship("Intervention")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id])

    __table_args__ = (
        Index("idx_post_works_links_completion", "completion_confirmation_id"),
        Index("idx_post_works_links_intervention", "intervention_id"),
        Index("idx_post_works_links_status", "status"),
    )
