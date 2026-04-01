"""
BatiConnect - Building Intent & Question Models

First-class models for intent queries: what does a human want to do with this building,
what questions must the system answer, what evidence supports the decision, and what
is the governed verdict?

These are native product concepts — the system must not only store and relate,
it must answer.
"""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# ---------------------------------------------------------------------------
# Enums as constants (used for validation at schema layer)
# ---------------------------------------------------------------------------

INTENT_TYPES = (
    "sell",
    "buy",
    "renovate",
    "insure",
    "finance",
    "lease",
    "transfer",
    "demolish",
    "assess",
    "comply",
    "maintain",
    "remediate",
    "other",
)

INTENT_STATUSES = ("open", "evaluating", "answered", "deferred", "closed")

QUESTION_TYPES = (
    "safe_to_start",
    "safe_to_sell",
    "safe_to_insure",
    "safe_to_finance",
    "safe_to_lease",
    "safe_to_transfer",
    "safe_to_demolish",
    "safe_to_tender",
    "what_blocks",
    "what_missing",
    "what_contradicts",
    "what_changed",
    "what_expires",
    "what_costs",
    "what_next",
    "custom",
)

QUESTION_STATUSES = ("pending", "evaluating", "answered", "stale")

SAFE_TO_TYPES = (
    "start",
    "sell",
    "insure",
    "finance",
    "lease",
    "transfer",
    "demolish",
    "tender",
    "reopen",
    "requalify",
)

VERDICT_VALUES = ("clear", "conditional", "blocked", "unknown")

DATA_FRESHNESS_VALUES = ("current", "aging", "stale", "expired")

COVERAGE_VALUES = ("complete", "partial", "insufficient")


class BuildingIntent(Base):
    """A human purpose that the system must serve."""

    __tablename__ = "building_intents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    intent_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime, nullable=True)

    status = Column(String(30), nullable=False, default="open")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building")
    organization = relationship("Organization")
    created_by = relationship("User")
    questions = relationship("BuildingQuestion", back_populates="intent", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_building_intents_building_status", "building_id", "status"),)


class BuildingQuestion(Base):
    """A specific query the system must answer about a building."""

    __tablename__ = "building_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("building_intents.id"), nullable=True, index=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    asked_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    question_type = Column(String(50), nullable=False)
    question_text = Column(String(500), nullable=False)

    status = Column(String(30), nullable=False, default="pending")
    answered_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    intent = relationship("BuildingIntent", back_populates="questions")
    building = relationship("Building")
    asked_by = relationship("User")
    decision_context = relationship(
        "DecisionContext", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )
    safe_to_x_state = relationship(
        "SafeToXState", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_building_questions_building_status", "building_id", "status"),)


class DecisionContext(Base):
    """The assembled evidence, claims, rules, and constraints relevant to a decision."""

    __tablename__ = "decision_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("building_questions.id"), nullable=False, unique=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    # Assembled basis
    relevant_evidence_ids = Column(JSON, nullable=True)
    relevant_claims_ids = Column(JSON, nullable=True)
    applicable_rules = Column(JSON, nullable=True)
    blockers = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)

    # Trust assessment
    overall_confidence = Column(Float, nullable=True)
    data_freshness = Column(String(20), nullable=True)
    contradiction_count = Column(Integer, default=0)
    coverage_assessment = Column(String(20), nullable=True)

    computed_at = Column(DateTime, default=func.now())

    # Relationships
    question = relationship("BuildingQuestion", back_populates="decision_context")
    building = relationship("Building")


class SafeToXState(Base):
    """A governed readiness verdict for a specific intent."""

    __tablename__ = "safe_to_x_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("building_questions.id"), nullable=False, unique=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("building_intents.id"), nullable=True)

    safe_to_type = Column(String(30), nullable=False)

    # Verdict
    verdict = Column(String(20), nullable=False)
    verdict_summary = Column(String(500), nullable=False)

    # Basis
    decision_context_id = Column(UUID(as_uuid=True), ForeignKey("decision_contexts.id"), nullable=True)
    blockers = Column(JSON, nullable=True)  # [{description, severity, resolution_path}]
    conditions = Column(JSON, nullable=True)  # [{description, status, evidence_id}]

    # Provenance
    evaluated_at = Column(DateTime, default=func.now())
    evaluated_by = Column(String(20), default="system")  # system | user
    rule_basis = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)

    # Lifecycle & temporal validity
    observed_at = Column(DateTime, nullable=True, doc="When was this state observed/measured")
    effective_at = Column(DateTime, nullable=True, doc="When does this verdict take effect")
    valid_from = Column(DateTime, nullable=True, doc="Start of verdict validity window")
    valid_until = Column(DateTime, nullable=True)
    stale_after = Column(DateTime, nullable=True, doc="When does this verdict become unreliable")
    superseded_by_id = Column(UUID(as_uuid=True), ForeignKey("safe_to_x_states.id"), nullable=True)
    superseded_at = Column(DateTime, nullable=True, doc="When was this verdict superseded")

    created_at = Column(DateTime, default=func.now())

    # Relationships
    question = relationship("BuildingQuestion", back_populates="safe_to_x_state")
    building = relationship("Building")
    intent = relationship("BuildingIntent")
    decision_context = relationship("DecisionContext", foreign_keys=[decision_context_id])
    superseded_by = relationship("SafeToXState", remote_side="SafeToXState.id", uselist=False)

    __table_args__ = (Index("idx_safe_to_x_building_type", "building_id", "safe_to_type"),)
