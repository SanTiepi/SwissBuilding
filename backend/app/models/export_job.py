import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)  # building_dossier, handoff_pack, audit_pack
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    status = Column(String(20), nullable=False, default="queued")  # queued, processing, completed, failed
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

    requester = relationship("User", foreign_keys=[requested_by])
    building = relationship("Building")
    organization = relationship("Organization")

    __table_args__ = (
        Index("idx_export_jobs_status", "status"),
        Index("idx_export_jobs_requested_by", "requested_by"),
    )
