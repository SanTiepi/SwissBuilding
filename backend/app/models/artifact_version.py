"""Artifact Versioning — ArtifactVersion model.

Tracks every outbound artifact version with content hash, status lifecycle,
and supersession chain.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_type = Column(String(50), nullable=False, index=True)
    artifact_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=True)  # SHA-256
    status = Column(String(20), nullable=False, default="current")  # current|superseded|archived|withdrawn
    superseded_by_id = Column(UUID(as_uuid=True), ForeignKey("artifact_versions.id"), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    archived_at = Column(DateTime, nullable=True)
    archive_reason = Column(Text, nullable=True)

    superseded_by = relationship("ArtifactVersion", remote_side=[id], foreign_keys=[superseded_by_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    custody_events = relationship(
        "CustodyEvent", back_populates="artifact_version", order_by="CustodyEvent.occurred_at"
    )
