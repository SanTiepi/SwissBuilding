"""Adoption Loops — Bounded embed tokens and external viewer profiles."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class ExternalViewerProfile(Base):
    __tablename__ = "external_viewer_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    viewer_type = Column(String(30), nullable=False)  # partner | authority | insurer | lender | buyer | other
    allowed_sections = Column(JSON, nullable=True)
    requires_acknowledgement = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class BoundedEmbedToken(Base):
    __tablename__ = "bounded_embed_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    token = Column(String(100), unique=True, nullable=False, index=True)
    viewer_profile_id = Column(UUID(as_uuid=True), ForeignKey("external_viewer_profiles.id"), nullable=True)
    scope = Column(JSON, nullable=True)  # {sections: [str], max_views: int|null, expires_at: str|null}
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    view_count = Column(Integer, default=0)
    last_viewed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
