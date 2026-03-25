import uuid

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CommitteeDecisionPack(Base):
    __tablename__ = "committee_decision_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    committee_name = Column(String(200), nullable=False)
    committee_type = Column(
        String(30), nullable=False
    )  # municipal_council | building_committee | procurement_committee | technical_commission | other
    pack_version = Column(Integer, default=1)
    status = Column(String(20), default="draft")  # draft | submitted | under_review | decided | archived
    sections = Column(JSON, nullable=True)
    procurement_clauses = Column(JSON, nullable=True)
    content_hash = Column(String(64), nullable=True)
    decision_deadline = Column(Date, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")


class ReviewDecisionTrace(Base):
    __tablename__ = "review_decision_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pack_type = Column(String(30), nullable=False)  # committee | municipal_review
    pack_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reviewer_name = Column(String(200), nullable=False)
    reviewer_role = Column(String(100), nullable=True)
    reviewer_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    decision = Column(String(20), nullable=False)  # approved | rejected | deferred | modified | abstained
    conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    evidence_refs = Column(JSON, nullable=True)
    confidence_level = Column(String(20), nullable=True)
    decided_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    reviewer_org = relationship("Organization")
