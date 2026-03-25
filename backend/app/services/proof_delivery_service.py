"""BatiConnect — Proof Delivery service."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proof_delivery import ProofDelivery


def compute_content_hash(content: str | bytes) -> str:
    """Compute SHA-256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


async def create_delivery(
    db: AsyncSession,
    building_id: UUID,
    data: dict,
    created_by: UUID | None = None,
) -> ProofDelivery:
    """Queue a new proof delivery."""
    data.pop("building_id", None)
    delivery = ProofDelivery(
        building_id=building_id,
        created_by=created_by,
        status="queued",
        **data,
    )
    # Compute content_hash if target content is available
    if not delivery.content_hash:
        # Hash the target reference as a placeholder — real implementations
        # would hash the actual file/pack content at send time.
        delivery.content_hash = compute_content_hash(f"{delivery.target_type}:{delivery.target_id}")
    db.add(delivery)
    await db.flush()
    await db.refresh(delivery)

    # Custody tracking: record delivered event for the target artifact
    try:
        from app.services.artifact_custody_service import get_current_version, record_custody_event

        current = await get_current_version(db, delivery.target_type, delivery.target_id)
        if current:
            await record_custody_event(
                db,
                current.id,
                {"event_type": "delivered", "actor_type": "system", "details": {"delivery_id": str(delivery.id)}},
            )
    except Exception:
        pass  # Non-fatal

    return delivery


async def get_delivery(db: AsyncSession, delivery_id: UUID) -> ProofDelivery | None:
    result = await db.execute(select(ProofDelivery).where(ProofDelivery.id == delivery_id))
    return result.scalar_one_or_none()


async def get_deliveries_for_building(
    db: AsyncSession,
    building_id: UUID,
    *,
    audience: str | None = None,
    status: str | None = None,
) -> list[ProofDelivery]:
    """Get delivery history for a building."""
    query = select(ProofDelivery).where(ProofDelivery.building_id == building_id)
    if audience:
        query = query.where(ProofDelivery.audience == audience)
    if status:
        query = query.where(ProofDelivery.status == status)
    query = query.order_by(ProofDelivery.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_deliveries_for_target(
    db: AsyncSession,
    target_type: str,
    target_id: UUID,
) -> list[ProofDelivery]:
    """Get all deliveries for a specific target (document/pack/etc)."""
    query = (
        select(ProofDelivery)
        .where(ProofDelivery.target_type == target_type, ProofDelivery.target_id == target_id)
        .order_by(ProofDelivery.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def mark_sent(db: AsyncSession, delivery_id: UUID, **kwargs) -> ProofDelivery | None:
    delivery = await get_delivery(db, delivery_id)
    if not delivery:
        return None
    delivery.status = "sent"
    delivery.sent_at = datetime.now(UTC)
    if kwargs.get("notes"):
        delivery.notes = kwargs["notes"]
    await db.flush()
    await db.refresh(delivery)
    return delivery


async def mark_delivered(db: AsyncSession, delivery_id: UUID, **kwargs) -> ProofDelivery | None:
    delivery = await get_delivery(db, delivery_id)
    if not delivery:
        return None
    delivery.status = "delivered"
    delivery.delivered_at = datetime.now(UTC)
    if kwargs.get("notes"):
        delivery.notes = kwargs["notes"]
    await db.flush()
    await db.refresh(delivery)
    return delivery


async def mark_viewed(db: AsyncSession, delivery_id: UUID, **kwargs) -> ProofDelivery | None:
    delivery = await get_delivery(db, delivery_id)
    if not delivery:
        return None
    delivery.status = "viewed"
    delivery.viewed_at = datetime.now(UTC)
    if kwargs.get("notes"):
        delivery.notes = kwargs["notes"]
    await db.flush()
    await db.refresh(delivery)
    return delivery


async def mark_acknowledged(db: AsyncSession, delivery_id: UUID, **kwargs) -> ProofDelivery | None:
    delivery = await get_delivery(db, delivery_id)
    if not delivery:
        return None
    delivery.status = "acknowledged"
    delivery.acknowledged_at = datetime.now(UTC)
    if kwargs.get("notes"):
        delivery.notes = kwargs["notes"]
    await db.flush()
    await db.refresh(delivery)

    # Custody tracking: record acknowledged event
    try:
        from app.services.artifact_custody_service import get_current_version, record_custody_event

        current = await get_current_version(db, delivery.target_type, delivery.target_id)
        if current:
            await record_custody_event(
                db,
                current.id,
                {"event_type": "acknowledged", "actor_type": "system", "details": {"delivery_id": str(delivery.id)}},
            )
    except Exception:
        pass  # Non-fatal

    return delivery


async def mark_failed(db: AsyncSession, delivery_id: UUID, error_message: str, **kwargs) -> ProofDelivery | None:
    delivery = await get_delivery(db, delivery_id)
    if not delivery:
        return None
    delivery.status = "failed"
    delivery.error_message = error_message
    if kwargs.get("notes"):
        delivery.notes = kwargs["notes"]
    await db.flush()
    await db.refresh(delivery)
    return delivery
