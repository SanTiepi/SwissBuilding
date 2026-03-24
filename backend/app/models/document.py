import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    document_type = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    processing_metadata = Column(JSON, nullable=True)  # {virus_scan: {...}, ocr: {...}}
    content_hash = Column(String(64), nullable=True)  # SHA-256 for identity/dedup
    created_at = Column(DateTime, default=func.now())

    building = relationship("Building", back_populates="documents")

    __table_args__ = (
        # Partial unique: (content_hash, file_path) when content_hash IS NOT NULL
        Index(
            "uq_documents_content_hash_file_path",
            "content_hash",
            "file_path",
            unique=True,
            postgresql_where=Column("content_hash").isnot(None),
        ),
    )
