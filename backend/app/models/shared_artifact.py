"""Time-limited read-only share link for generated pack artifacts (PDF/JSON)."""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class SharedArtifact(Base):
    """A time-limited read-only share link for a generated artifact."""

    __tablename__ = "shared_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), nullable=False)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), nullable=False)

    # What's shared
    artifact_type = Column(String(50), nullable=False)  # authority_pack, transaction_pack
    artifact_data = Column(JSON, nullable=False)  # the pack data (serialised)

    # Access
    access_token = Column(String(64), unique=True, nullable=False, index=True)

    # Expiry
    expires_at = Column(DateTime, nullable=False)  # default: 7 days

    # Metadata
    title = Column(String(255), nullable=False)
    redacted = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=func.now())
