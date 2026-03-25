"""BatiConnect — Marketplace: Client Request (RFQ) model."""

import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ClientRequest(Base):
    __tablename__ = "client_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    requester_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requester_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    pollutant_types = Column(JSON, nullable=True)  # ["asbestos","pcb","lead","hap","radon","pfas"]
    work_category = Column(String(50), nullable=False)  # minor | medium | major (CFST 6503)
    estimated_area_m2 = Column(Float, nullable=True)
    deadline = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="draft")  # draft | published | closed | awarded | cancelled
    diagnostic_publication_id = Column(
        UUID(as_uuid=True), ForeignKey("diagnostic_report_publications.id"), nullable=True
    )
    budget_indication = Column(String(50), nullable=True)  # under_10k | 10k_50k | 50k_100k | 100k_500k | over_500k
    site_access_notes = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    requester_user = relationship("User", foreign_keys=[requester_user_id])
    requester_org = relationship("Organization", foreign_keys=[requester_org_id])
    diagnostic_publication = relationship("DiagnosticReportPublication")
    documents = relationship("RequestDocument", back_populates="client_request")
    invitations = relationship("RequestInvitation", back_populates="client_request")
    quotes = relationship("Quote", back_populates="client_request")
