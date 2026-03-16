"""Generic background job tracking model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.database import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(
        String(100), nullable=False
    )  # pack_generation, search_sync, signal_generation, dossier_completion
    status = Column(String(50), nullable=False, default="queued")  # queued, running, completed, failed, cancelled
    building_id = Column(UUID(as_uuid=True), nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    params_json = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    progress_pct = Column(Integer, nullable=True)  # 0-100
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_background_jobs_job_type", "job_type"),
        Index("idx_background_jobs_status", "status"),
        Index("idx_background_jobs_building_id", "building_id"),
    )
