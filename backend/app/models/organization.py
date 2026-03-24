import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(
        String(50), nullable=False
    )  # diagnostic_lab, architecture_firm, property_management, authority, contractor
    address = Column(String(500))
    postal_code = Column(String(10))
    city = Column(String(100))
    canton = Column(String(2))
    phone = Column(String(20))
    email = Column(String(255))
    suva_recognized = Column(Boolean, default=False)
    fach_approved = Column(Boolean, default=False)
    contact_person_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", use_alter=True), nullable=True)
    created_at = Column(DateTime, default=func.now())

    members = relationship("User", back_populates="organization")
    contact_person = relationship("Contact", foreign_keys=[contact_person_id])
