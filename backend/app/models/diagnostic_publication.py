import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base
from app.models.mixins import ProvenanceMixin


class DiagnosticReportPublication(ProvenanceMixin, Base):
    __tablename__ = "diagnostic_report_publications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True, index=True)
    source_system = Column(String(50), default="batiscan")
    source_mission_id = Column(String(100), nullable=False)
    current_version = Column(Integer, default=1)
    match_state = Column(String(20), nullable=False)  # auto_matched | manual_matched | needs_review | unmatched
    match_key = Column(String(100), nullable=True)
    match_key_type = Column(String(20), nullable=False)  # egid | egrid | address | manual | none
    report_pdf_url = Column(String(500), nullable=True)
    structured_summary = Column(JSON, nullable=True)
    annexes = Column(JSON, nullable=True)
    payload_hash = Column(String(64), nullable=False)
    mission_type = Column(
        String(50), nullable=False
    )  # asbestos_full | asbestos_complement | pcb | lead | hap | radon | pfas | multi
    published_at = Column(DateTime(timezone=True), nullable=False)
    is_immutable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="diagnostic_publications")
    versions = relationship(
        "DiagnosticPublicationVersion", back_populates="publication", order_by="DiagnosticPublicationVersion.version"
    )
