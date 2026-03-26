"""Dossier version — immutable snapshot of a building dossier at a point in time."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class DossierVersion(Base):
    __tablename__ = "dossier_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    label = Column(String(100), nullable=True)  # e.g., "Pre-renovation", "Post-works", "Authority submission"
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    snapshot_data = Column(JSON, nullable=False)  # Full dossier state as JSON
    completeness_score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
