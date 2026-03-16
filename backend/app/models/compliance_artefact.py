import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ComplianceArtefact(Base):
    __tablename__ = "compliance_artefacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # Type and status
    artefact_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="draft")

    # Content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)

    # Related entities
    diagnostic_id = Column(UUID(as_uuid=True), ForeignKey("diagnostics.id"), nullable=True)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("interventions.id"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    # Authority info
    authority_name = Column(String(255), nullable=True)
    authority_type = Column(String(50), nullable=True)

    # Timeline
    submitted_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Legal basis
    legal_basis = Column(String(255), nullable=True)

    # Metadata
    metadata_json = Column(JSON, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")

    __table_args__ = (
        Index("idx_compliance_artefacts_building_id", "building_id"),
        Index("idx_compliance_artefacts_type_status", "artefact_type", "status"),
    )
