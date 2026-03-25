"""Commune Adapter — CommunalAdapterProfile model."""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class CommunalAdapterProfile(Base):
    __tablename__ = "communal_adapter_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commune_code = Column(String(10), nullable=False)
    commune_name = Column(String(200), nullable=False)
    canton_code = Column(String(2), nullable=False)
    adapter_status = Column(String(20), nullable=False, default="draft")  # active|draft|review_only|inactive
    supports_procedure_projection = Column(Boolean, default=False)
    supports_rule_projection = Column(Boolean, default=False)
    fallback_mode = Column(String(20), nullable=False, default="canton_default")  # manual_review|canton_default|none
    source_ids = Column(JSON, nullable=True)  # linked RuleSource ids
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
