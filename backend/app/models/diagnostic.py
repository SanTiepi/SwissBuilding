import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Diagnostic(Base):
    __tablename__ = "diagnostics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    diagnostic_type = Column(String(50), nullable=False)
    diagnostic_context = Column(String(10), default="AvT")
    status = Column(String(20), default="draft")
    diagnostician_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    laboratory = Column(String(255), nullable=True)
    laboratory_report_number = Column(String(100), nullable=True)
    date_inspection = Column(Date, nullable=True)
    date_report = Column(Date, nullable=True)
    report_file_path = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    conclusion = Column(String(50), nullable=True)
    methodology = Column(String(100), nullable=True)
    suva_notification_required = Column(Boolean, default=False)
    suva_notification_date = Column(Date, nullable=True)
    canton_notification_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building", back_populates="diagnostics")
    diagnostician = relationship("User", back_populates="diagnostics", foreign_keys=[diagnostician_id])
    samples = relationship("Sample", back_populates="diagnostic", cascade="all, delete-orphan")
