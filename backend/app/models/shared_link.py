"""Time-limited audience-bounded sharing links."""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class SharedLink(Base):
    __tablename__ = "shared_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), unique=True, nullable=False, index=True)

    # What is shared
    resource_type = Column(String(50), nullable=False)  # building, diagnostic, passport, authority_pack
    resource_id = Column(UUID(as_uuid=True), nullable=False)

    # Who created it
    created_by = Column(UUID(as_uuid=True), nullable=False)
    organization_id = Column(UUID(as_uuid=True), nullable=True)

    # Audience constraints
    audience_type = Column(String(50), nullable=False)  # buyer, insurer, lender, authority, contractor, tenant
    audience_email = Column(String(255), nullable=True)  # optional email restriction

    # Access constraints
    expires_at = Column(DateTime, nullable=False)
    max_views = Column(Integer, nullable=True)  # optional view limit
    view_count = Column(Integer, default=0)

    # Scope constraints
    allowed_sections = Column(JSON, nullable=True)  # which sections are visible

    # State
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_accessed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_shared_link_resource", "resource_type", "resource_id"),
        Index("idx_shared_link_created_by", "created_by"),
    )
