"""BatiConnect — Intake Request model for public diagnostic request submissions."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class IntakeRequest(Base):
    __tablename__ = "intake_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), nullable=False, default="new")  # new|qualified|converted|rejected|spam
    requester_name = Column(String(200), nullable=False)
    requester_email = Column(String(200), nullable=False)
    requester_phone = Column(String(50), nullable=True)
    requester_company = Column(String(200), nullable=True)
    building_address = Column(String(500), nullable=False)
    building_egid = Column(String(20), nullable=True)
    building_city = Column(String(100), nullable=True)
    building_postal_code = Column(String(10), nullable=True)
    request_type = Column(
        String(50), nullable=False
    )  # asbestos_diagnostic|pcb_diagnostic|lead_diagnostic|multi_pollutant|consultation|other
    description = Column(Text, nullable=True)
    urgency = Column(String(20), nullable=False, default="standard")  # standard|urgent|emergency
    attachments = Column(JSON, nullable=True)
    converted_contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    converted_building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True)
    converted_mission_order_id = Column(UUID(as_uuid=True), nullable=True)
    qualified_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    qualified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, default="website")  # website|email|phone|referral|other
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_intake_requests_status", "status"),
        Index("idx_intake_requests_email", "requester_email"),
        Index("idx_intake_requests_created_at", "created_at"),
    )
