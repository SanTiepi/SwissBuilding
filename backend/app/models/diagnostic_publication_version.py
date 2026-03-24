import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class DiagnosticPublicationVersion(Base):
    __tablename__ = "diagnostic_publication_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_id = Column(
        UUID(as_uuid=True), ForeignKey("diagnostic_report_publications.id"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    report_pdf_url = Column(String(500), nullable=True)
    structured_summary = Column(JSON, nullable=True)
    annexes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())

    publication = relationship("DiagnosticReportPublication", back_populates="versions")
