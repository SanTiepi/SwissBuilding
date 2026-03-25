"""BatiConnect — Marketplace: Subscription Change audit model."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class SubscriptionChange(Base):
    __tablename__ = "subscription_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("company_subscriptions.id"), nullable=False, index=True)
    change_type = Column(
        String(30), nullable=False
    )  # created | plan_changed | suspended | reactivated | expired | cancelled
    old_plan = Column(String(30), nullable=True)
    new_plan = Column(String(30), nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
