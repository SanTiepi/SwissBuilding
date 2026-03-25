"""BatiConnect — Partner Webhook service.

Subscription management, event delivery with HMAC signing, retry logic.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.partner_webhook import PartnerDeliveryAttempt, PartnerWebhookSubscription


async def create_subscription(db: AsyncSession, data: dict) -> PartnerWebhookSubscription:
    sub = PartnerWebhookSubscription(**data)
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def list_subscriptions(db: AsyncSession, org_id: uuid.UUID | None = None) -> list[PartnerWebhookSubscription]:
    query = select(PartnerWebhookSubscription).order_by(PartnerWebhookSubscription.created_at.desc())
    if org_id:
        query = query.where(PartnerWebhookSubscription.partner_org_id == org_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_subscription(db: AsyncSession, sub_id: uuid.UUID) -> bool:
    sub = await db.get(PartnerWebhookSubscription, sub_id)
    if not sub:
        return False
    await db.delete(sub)
    await db.flush()
    return True


def _sign_payload(secret: str, payload: dict) -> str:
    """Compute HMAC-SHA256 signature for the payload."""
    body = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def deliver_event(db: AsyncSession, event_type: str, payload: dict) -> list[PartnerDeliveryAttempt]:
    """For each active subscription matching event_type: create delivery attempt."""
    result = await db.execute(select(PartnerWebhookSubscription).where(PartnerWebhookSubscription.is_active.is_(True)))
    subs = result.scalars().all()

    attempts = []
    for sub in subs:
        subscribed = sub.subscribed_events or []
        if event_type not in subscribed and "*" not in subscribed:
            continue

        idempotency_key = f"{sub.id}-{event_type}-{uuid.uuid4().hex[:12]}"
        signature = _sign_payload(sub.hmac_secret, payload)

        # In production, we would POST to sub.endpoint_url here.
        # For now, record the attempt as delivered (simulated).
        attempt = PartnerDeliveryAttempt(
            subscription_id=sub.id,
            event_type=event_type,
            idempotency_key=idempotency_key,
            payload={**payload, "_signature": signature},
            status="delivered",
            http_status=200,
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
        )
        db.add(attempt)
        attempts.append(attempt)

    if attempts:
        await db.flush()
        for a in attempts:
            await db.refresh(a)
    return attempts


async def retry_failed(db: AsyncSession, attempt_id: uuid.UUID) -> PartnerDeliveryAttempt | None:
    """Retry a failed delivery attempt with same idempotency key."""
    attempt = await db.get(PartnerDeliveryAttempt, attempt_id)
    if not attempt or attempt.status not in ("failed", "retrying"):
        return None

    attempt.status = "retrying"
    attempt.attempt_count += 1
    attempt.last_attempt_at = datetime.now(UTC)

    # Simulated retry — in production would POST again
    attempt.status = "delivered"
    attempt.http_status = 200

    await db.flush()
    await db.refresh(attempt)
    return attempt


async def get_delivery_history(db: AsyncSession, subscription_id: uuid.UUID) -> list[PartnerDeliveryAttempt]:
    result = await db.execute(
        select(PartnerDeliveryAttempt)
        .where(PartnerDeliveryAttempt.subscription_id == subscription_id)
        .order_by(PartnerDeliveryAttempt.created_at.desc())
    )
    return list(result.scalars().all())
