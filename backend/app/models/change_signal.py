import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ChangeSignal(Base):
    __tablename__ = "change_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="info")
    status = Column(String(20), nullable=False, default="active")

    # Context
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)

    # Related entity (polymorphic)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Metadata
    metadata_json = Column(JSON, nullable=True)
    detected_at = Column(DateTime, default=func.now())
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    building = relationship("Building")
