import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # action, invitation, export, system
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="unread")  # unread, read
    created_at = Column(DateTime, default=func.now())
    read_at = Column(DateTime, nullable=True)

    user = relationship("User")

    __table_args__ = (Index("idx_notifications_user_status", "user_id", "status"),)


class NotificationPreferenceExtended(Base):
    __tablename__ = "notification_preferences_extended"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    preferences_json = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    in_app_actions = Column(Boolean, default=True)
    in_app_invitations = Column(Boolean, default=True)
    in_app_exports = Column(Boolean, default=True)
    digest_enabled = Column(Boolean, default=False)

    user = relationship("User")
