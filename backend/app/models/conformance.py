"""BatiConnect — Conformance Check models.

RequirementProfile = a named set of requirements that a pack/publication/import/exchange must satisfy.
ConformanceCheck = result of verifying an artifact against a requirement profile.

Machine-readable, auditable, no promise of legal certification.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class RequirementProfile(Base):
    """A named, inspectable set of requirements for conformance checking."""

    __tablename__ = "requirement_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    profile_type = Column(String(50), nullable=False)  # pack | import | publication | exchange | procedure

    # Requirements
    required_sections = Column(JSON, nullable=True)  # sections that must be present
    required_fields = Column(JSON, nullable=True)  # fields that must be non-null
    minimum_completeness = Column(Float, nullable=True)  # min completeness % (0-1)
    minimum_trust = Column(Float, nullable=True)  # min trust % (0-1)
    required_readiness = Column(JSON, nullable=True)  # e.g. {"safe_to_start": "clear"}
    max_unknowns = Column(Integer, nullable=True)  # max allowed open unknowns
    max_contradictions = Column(Integer, nullable=True)  # max allowed open contradictions
    redaction_allowed = Column(Boolean, nullable=False, default=True)

    active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_req_profiles_name", "name"),
        Index("idx_req_profiles_type", "profile_type"),
        Index("idx_req_profiles_active", "active"),
    )


class ConformanceCheck(Base):
    """Result of checking an artifact against a requirement profile."""

    __tablename__ = "conformance_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("requirement_profiles.id"), nullable=False)
    checked_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    target_type = Column(String(50), nullable=False)  # pack | passport | import | publication
    target_id = Column(UUID(as_uuid=True), nullable=True)  # ID of the artifact checked

    # Result
    result = Column(String(20), nullable=False)  # pass | fail | partial
    score = Column(Float, nullable=False, default=0.0)  # 0-1 conformance score

    # Details
    checks_passed = Column(JSON, nullable=True)  # [{"check": ..., "status": "pass"}]
    checks_failed = Column(JSON, nullable=True)  # [{"check": ..., "status": "fail", "reason": ...}]
    checks_warning = Column(JSON, nullable=True)  # [{"check": ..., "status": "warning", "reason": ...}]

    summary = Column(Text, nullable=True)

    checked_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    building = relationship("Building")
    profile = relationship("RequirementProfile")
    checked_by = relationship("User")

    __table_args__ = (
        Index("idx_conformance_building_id", "building_id"),
        Index("idx_conformance_profile_id", "profile_id"),
        Index("idx_conformance_result", "result"),
        Index("idx_conformance_target", "target_type", "target_id"),
        Index("idx_conformance_building_profile", "building_id", "profile_id"),
    )
