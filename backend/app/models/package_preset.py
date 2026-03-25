"""Adoption Loops — Buyer packaging: package presets for audience-tailored views."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class PackagePreset(Base):
    __tablename__ = "package_presets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    preset_code = Column(String(50), unique=True, nullable=False)  # wedge | operational | portfolio
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    audience_type = Column(String(30), nullable=False)  # owner | manager | authority | insurer | fiduciary | contractor
    included_sections = Column(JSON, nullable=True)
    excluded_sections = Column(JSON, nullable=True)
    unknown_sections = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
