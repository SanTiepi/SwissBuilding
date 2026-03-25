"""BatiConnect — Passport State Diff model.

Tracks computed diffs between consecutive passport publications.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class PassportStateDiff(Base):
    __tablename__ = "passport_state_diffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_id = Column(UUID(as_uuid=True), ForeignKey("passport_publications.id"), nullable=False, index=True)
    prior_publication_id = Column(UUID(as_uuid=True), ForeignKey("passport_publications.id"), nullable=True)
    diff_summary = Column(JSON, nullable=True)
    sections_changed_count = Column(Integer, default=0)
    computed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    publication = relationship("PassportPublication", foreign_keys=[publication_id])
    prior_publication = relationship("PassportPublication", foreign_keys=[prior_publication_id])
