"""GED Inbox — Document inbox for unlinked incoming documents."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DocumentInboxItem(Base):
    __tablename__ = "document_inbox_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)

    # pending | classified | linked | rejected
    status = Column(String(20), nullable=False, default="pending")

    # AI/auto suggestion vs confirmed link
    suggested_building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True)
    linked_building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True)
    linked_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    # {document_type, confidence, tags}
    classification = Column(JSON, nullable=True)

    # upload | email | api | batiscan
    source = Column(String(50), nullable=False, default="upload")

    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    suggested_building = relationship("Building", foreign_keys=[suggested_building_id])
    linked_building = relationship("Building", foreign_keys=[linked_building_id])
    linked_document = relationship("Document", foreign_keys=[linked_document_id])
    uploaded_by_user = relationship("User", foreign_keys=[uploaded_by_user_id])

    __table_args__ = (
        Index("ix_document_inbox_items_status", "status"),
        Index("ix_document_inbox_items_source", "source"),
    )
