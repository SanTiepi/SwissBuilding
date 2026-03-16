"""Evidence pack model — structured proof-pack definitions for authority/contractor handoff."""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EvidencePack(Base):
    __tablename__ = "evidence_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    pack_type = Column(String(50), nullable=False)  # authority_pack, contractor_pack, owner_pack
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")  # draft, assembling, complete, submitted, expired

    # Pack content specification
    required_sections_json = Column(JSON, nullable=True)  # [{section_type, label, required, included}]
    included_artefacts_json = Column(JSON, nullable=True)  # [{artefact_type, artefact_id, status}]
    included_documents_json = Column(JSON, nullable=True)  # [{document_id, document_type}]

    # Recipient info
    recipient_name = Column(String(255), nullable=True)
    recipient_type = Column(String(50), nullable=True)  # authority, contractor, owner, insurer
    recipient_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # Export linkage
    export_job_id = Column(UUID(as_uuid=True), ForeignKey("export_jobs.id"), nullable=True)

    # Metadata
    assembled_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    notes = Column(Text, nullable=True)

    building = relationship("Building")
