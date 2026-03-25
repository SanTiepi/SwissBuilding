"""Artifact Versioning — CustodyEvent model.

Records each chain-of-custody event for an artifact version:
created, published, delivered, viewed, acknowledged, disputed,
superseded, archived, withdrawn.
"""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_version_id = Column(UUID(as_uuid=True), ForeignKey("artifact_versions.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    actor_type = Column(String(30), nullable=False, default="system")
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_name = Column(String(200), nullable=True)
    recipient_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    details = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=func.now())
    created_at = Column(DateTime, nullable=False, default=func.now())

    artifact_version = relationship("ArtifactVersion", back_populates="custody_events")
    recipient_org = relationship("Organization", foreign_keys=[recipient_org_id])
