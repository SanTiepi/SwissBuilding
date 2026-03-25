"""Finance Surfaces — Audience Pack model.

Audience-tailored intelligence packs for external stakeholders
(insurer, fiduciary, transaction, lender). Extends PackagePreset
by providing materialized, versioned, redaction-aware snapshots.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class AudiencePack(Base):
    __tablename__ = "audience_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    pack_type = Column(String(30), nullable=False)  # insurer | fiduciary | transaction | lender
    pack_version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="draft")  # draft | ready | shared | acknowledged | archived

    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Assembled sections (building identity, diagnostics summary, obligations, etc.)
    sections = Column(JSON, nullable=False)

    # Summaries computed at generation time
    unknowns_summary = Column(JSON, nullable=True)  # [{type, description, impact}]
    contradictions_summary = Column(JSON, nullable=True)  # [{type, description, severity}]
    residual_risk_summary = Column(JSON, nullable=True)  # [{risk_type, description, mitigation}]
    trust_refs = Column(JSON, nullable=True)  # [{entity_type, entity_id, confidence, freshness}]
    proof_refs = Column(JSON, nullable=True)  # [{document_id, label, version, freshness_state}]

    # Integrity
    content_hash = Column(String(64), nullable=False)
    generated_at = Column(DateTime, nullable=False, default=func.now())

    # Versioning chain
    superseded_by_id = Column(UUID(as_uuid=True), ForeignKey("audience_packs.id"), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_audience_packs_building_id", "building_id"),
        Index("idx_audience_packs_type", "pack_type"),
        Index("idx_audience_packs_status", "status"),
        Index("idx_audience_packs_building_type", "building_id", "pack_type"),
    )
