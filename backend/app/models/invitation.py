import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, accepted, expired, revoked
    token = Column(String(255), nullable=False, unique=True, index=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    inviter = relationship("User", foreign_keys=[invited_by])
    organization = relationship("Organization")

    __table_args__ = (
        Index("idx_invitations_email", "email"),
        Index("idx_invitations_status", "status"),
    )
