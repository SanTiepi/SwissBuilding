import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class Contact(ProvenanceMixin, Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    contact_type = Column(
        String(30), nullable=False
    )  # person | company | authority | notary | insurer | syndic | supplier
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    postal_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    canton = Column(String(2), nullable=True)
    external_ref = Column(String(100), nullable=True)
    linked_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    organization = relationship("Organization", foreign_keys=[organization_id])
    linked_user = relationship("User", foreign_keys=[linked_user_id])

    __table_args__ = (
        Index("idx_contacts_email", "email"),
        Index("idx_contacts_contact_type", "contact_type"),
        # Partial unique: (email, organization_id) when email IS NOT NULL
        Index(
            "uq_contacts_email_org",
            "email",
            "organization_id",
            unique=True,
            postgresql_where=Column("email").isnot(None),
        ),
        # Partial unique: (external_ref, organization_id) when external_ref IS NOT NULL
        Index(
            "uq_contacts_external_ref_org",
            "external_ref",
            "organization_id",
            unique=True,
            postgresql_where=Column("external_ref").isnot(None),
        ),
    )
