"""BatiConnect — Marketplace: Request Document model."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RequestDocument(Base):
    __tablename__ = "request_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_request_id = Column(UUID(as_uuid=True), ForeignKey("client_requests.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=True)
    document_type = Column(
        String(50), nullable=False
    )  # specification | plan | diagnostic_report | photo | permit | other
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    client_request = relationship("ClientRequest", back_populates="documents")
    document = relationship("Document")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
