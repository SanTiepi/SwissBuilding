"""BatiConnect — Contributor Gateway models.

ContributorGatewayRequest: bounded access for external contributors.
ContributorSubmission: pending submissions from contributors.
ContributorReceipt: proof of acceptance linked to documents/evidence.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ContributorGatewayRequest(Base):
    __tablename__ = "contributor_gateway_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    contributor_type = Column(String(20), nullable=False)  # contractor|lab
    scope_description = Column(Text, nullable=True)
    access_token = Column(String(100), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="open")  # open|fulfilled|expired|cancelled
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    linked_procedure_id = Column(UUID(as_uuid=True), nullable=True)
    linked_remediation_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    created_by = relationship("User")
    submissions = relationship("ContributorSubmission", back_populates="request")


class ContributorSubmission(Base):
    __tablename__ = "contributor_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("contributor_gateway_requests.id"), nullable=False, index=True)
    contributor_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    contributor_name = Column(String(200), nullable=True)
    submission_type = Column(
        String(50), nullable=False
    )  # completion_report|lab_results|certificate|attestation|photo_evidence|other
    file_url = Column(String(500), nullable=True)
    structured_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending_review")  # pending_review|accepted|rejected
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    request = relationship("ContributorGatewayRequest", back_populates="submissions")
    contributor_org = relationship("Organization")
    reviewed_by = relationship("User")
    receipt = relationship("ContributorReceipt", back_populates="submission", uselist=False)


class ContributorReceipt(Base):
    __tablename__ = "contributor_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("contributor_submissions.id"), nullable=False, unique=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    evidence_link_id = Column(UUID(as_uuid=True), nullable=True)
    proof_delivery_id = Column(UUID(as_uuid=True), nullable=True)
    receipt_hash = Column(String(64), nullable=False)
    accepted_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    submission = relationship("ContributorSubmission", back_populates="receipt")
    document = relationship("Document")
