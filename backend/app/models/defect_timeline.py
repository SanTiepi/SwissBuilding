import uuid

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DefectTimeline(Base):
    __tablename__ = "defect_timelines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    defect_type = Column(String(100), nullable=False)
    discovery_date = Column(Date, nullable=False)
    notification_deadline = Column(Date, nullable=False)
    notification_sent_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="open")
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="medium")
    responsible_party = Column(String(200), nullable=True)
    legal_reference = Column(String(100), nullable=False, default="art. 367 al. 1bis CO")
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="defect_timelines")

    __table_args__ = (
        Index("idx_defect_timelines_status", "status"),
        Index("idx_defect_timelines_deadline", "notification_deadline"),
    )
