import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PublicAssetGovernanceSignal(Base):
    __tablename__ = "public_asset_governance_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True, index=True)
    signal_type = Column(
        String(50), nullable=False
    )  # review_overdue | decision_pending | governance_gap | compliance_drift | proof_aging | procedure_stalled | committee_needed
    severity = Column(String(10), nullable=False, default="info")  # info | warning | critical
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    source_entity_type = Column(String(50), nullable=True)
    source_entity_id = Column(UUID(as_uuid=True), nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    organization = relationship("Organization")
    building = relationship("Building")
