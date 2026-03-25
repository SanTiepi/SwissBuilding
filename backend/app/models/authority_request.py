"""BatiConnect — AuthorityRequest model for complement/information requests within permit procedures."""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class AuthorityRequest(Base):
    __tablename__ = "authority_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    procedure_id = Column(UUID(as_uuid=True), ForeignKey("permit_procedures.id"), nullable=False, index=True)
    step_id = Column(UUID(as_uuid=True), ForeignKey("permit_steps.id"), nullable=True)
    request_type = Column(
        String(30), nullable=False
    )  # complement_request | information_request | clarification | correction
    from_authority = Column(Boolean, default=True)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    response_due_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="open")  # open | responded | overdue | closed
    response_body = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    linked_document_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    procedure = relationship("PermitProcedure", back_populates="authority_requests")
    step = relationship("PermitStep")

    __table_args__ = (
        Index("idx_authority_requests_status", "status"),
        Index("idx_authority_requests_type", "request_type"),
    )
