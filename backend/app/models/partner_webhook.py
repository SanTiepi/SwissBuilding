"""BatiConnect — Partner Webhook models.

PartnerWebhookSubscription: webhook endpoint + HMAC config.
PartnerDeliveryAttempt: delivery log per event dispatch.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class PartnerWebhookSubscription(Base):
    __tablename__ = "partner_webhook_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    endpoint_url = Column(String(500), nullable=False)
    hmac_secret = Column(String(100), nullable=False)
    subscribed_events = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    partner_org = relationship("Organization")
    delivery_attempts = relationship("PartnerDeliveryAttempt", back_populates="subscription")


class PartnerDeliveryAttempt(Base):
    __tablename__ = "partner_delivery_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(
        UUID(as_uuid=True), ForeignKey("partner_webhook_subscriptions.id"), nullable=False, index=True
    )
    event_type = Column(String(100), nullable=False)
    idempotency_key = Column(String(100), unique=True, nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending|delivered|failed|retrying
    http_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    subscription = relationship("PartnerWebhookSubscription", back_populates="delivery_attempts")
