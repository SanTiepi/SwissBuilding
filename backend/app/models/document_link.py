import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DocumentLink(Base):
    __tablename__ = "document_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    entity_type = Column(
        String(50), nullable=False
    )  # building | diagnostic | intervention | lease | contract | insurance_policy | claim | compliance_artefact | evidence_pack
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    link_type = Column(String(30), nullable=False)  # attachment | report | proof | reference | invoice | certificate
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    document = relationship("Document")

    __table_args__ = (
        UniqueConstraint("document_id", "entity_type", "entity_id", "link_type", name="uq_document_link"),
        Index("idx_document_links_entity", "entity_type", "entity_id"),
        Index("idx_document_links_document_id", "document_id"),
    )
