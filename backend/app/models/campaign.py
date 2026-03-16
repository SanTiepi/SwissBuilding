import uuid

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    priority = Column(String(20), nullable=False, default="medium")
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # Scope
    building_ids = Column(JSON, nullable=True)
    target_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)

    # Timeline
    date_start = Column(Date, nullable=True)
    date_end = Column(Date, nullable=True)

    # Budget
    budget_chf = Column(Float, nullable=True)
    spent_chf = Column(Float, nullable=True)

    # Metadata
    criteria_json = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    organization = relationship("Organization")

    __table_args__ = (
        Index("idx_campaigns_status", "status"),
        Index("idx_campaigns_organization_id", "organization_id"),
    )
