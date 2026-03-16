import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class ContractorAcknowledgment(Base):
    __tablename__ = "contractor_acknowledgments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("interventions.id"), nullable=False)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    contractor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Acknowledgment lifecycle
    status = Column(String(30), nullable=False, default="pending")
    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    refused_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Content
    safety_requirements = Column(JSON, nullable=False)
    contractor_notes = Column(Text, nullable=True)
    refusal_reason = Column(Text, nullable=True)

    # Evidence
    acknowledgment_hash = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_contractor_ack_building_id", "building_id"),
        Index("idx_contractor_ack_intervention_id", "intervention_id"),
        Index("idx_contractor_ack_contractor_user_id", "contractor_user_id"),
        Index("idx_contractor_ack_status", "status"),
    )
