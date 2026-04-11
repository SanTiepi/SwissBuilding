"""ConsequenceRun — records a consequence chain execution for a building."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ConsequenceRun(Base):
    __tablename__ = "consequence_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)

    trigger_type = Column(String(50), nullable=False)
    trigger_id = Column(String(255), nullable=True)
    triggered_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    result_json = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="completed")  # completed, partial, failed

    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
