"""Permit workflow service: CRUD + deadline tracking."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permit import Permit, PermitStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permit CRUD
# ---------------------------------------------------------------------------


async def create_permit(
    db: AsyncSession,
    building_id: UUID,
    *,
    permit_type: str,
    issued_date: datetime,
    expiry_date: datetime,
    subsidy_amount: float | None = None,
    notes: str | None = None,
) -> Permit:
    """Create a new permit."""
    # Validate dates
    if expiry_date <= issued_date:
        raise ValueError("expiry_date must be greater than issued_date")

    permit = Permit(
        building_id=building_id,
        permit_type=permit_type,
        issued_date=issued_date,
        expiry_date=expiry_date,
        status=PermitStatus.PENDING,
        subsidy_amount=subsidy_amount,
        notes=notes,
    )
    db.add(permit)
    await db.flush()
    await db.refresh(permit)

    logger.info("Created permit %s for building %s (%s)", permit.id, building_id, permit_type)
    return permit


async def get_permit(db: AsyncSession, permit_id: UUID) -> Permit | None:
    """Retrieve a single permit."""
    result = await db.execute(select(Permit).where(Permit.id == permit_id))
    return result.scalar_one_or_none()


async def get_building_permits(db: AsyncSession, building_id: UUID) -> list[Permit]:
    """List all permits for a building."""
    result = await db.execute(
        select(Permit)
        .where(Permit.building_id == building_id)
        .order_by(Permit.expiry_date)
    )
    return result.scalars().all()


async def update_permit(
    db: AsyncSession,
    permit_id: UUID,
    **updates,
) -> Permit | None:
    """Update permit fields."""
    permit = await get_permit(db, permit_id)
    if not permit:
        return None

    # Validate date relationship if both are updated
    issued_date = updates.get("issued_date", permit.issued_date)
    expiry_date = updates.get("expiry_date", permit.expiry_date)
    if expiry_date and issued_date and expiry_date <= issued_date:
        raise ValueError("expiry_date must be greater than issued_date")

    for key, value in updates.items():
        if hasattr(permit, key):
            setattr(permit, key, value)

    permit.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(permit)

    logger.info("Updated permit %s", permit_id)
    return permit


async def delete_permit(db: AsyncSession, permit_id: UUID) -> bool:
    """Delete a permit."""
    permit = await get_permit(db, permit_id)
    if not permit:
        return False

    await db.delete(permit)
    await db.flush()

    logger.info("Deleted permit %s", permit_id)
    return True


# ---------------------------------------------------------------------------
# Deadline Tracking
# ---------------------------------------------------------------------------


async def get_expiring_permits(
    db: AsyncSession,
    building_id: UUID,
    threshold_days: int = 30,
) -> list[Permit]:
    """List permits expiring within N days."""
    now = datetime.now(UTC)
    future = now + timedelta(days=threshold_days)

    result = await db.execute(
        select(Permit)
        .where(
            (Permit.building_id == building_id)
            & (Permit.expiry_date > now)
            & (Permit.expiry_date <= future)
            & (Permit.status != PermitStatus.EXPIRED)
            & (Permit.status != PermitStatus.REVOKED)
        )
        .order_by(Permit.expiry_date)
    )
    return result.scalars().all()


async def get_permit_alerts(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict]:
    """Get deadline alerts for permits (30/14/7 day markers)."""
    now = datetime.now(UTC)
    permits = await get_building_permits(db, building_id)

    alerts = []
    for permit in permits:
        if permit.status in (PermitStatus.EXPIRED, PermitStatus.REVOKED):
            continue

        days_until = (permit.expiry_date - now).days
        if days_until < 0:
            # Expired
            alert_level = "red"
        elif days_until <= 7:
            alert_level = "red"
        elif days_until <= 14:
            alert_level = "amber"
        elif days_until <= 30:
            alert_level = "amber"
        else:
            continue  # Not an alert

        alerts.append(
            {
                "permit_id": permit.id,
                "building_id": building_id,
                "permit_type": permit.permit_type,
                "expiry_date": permit.expiry_date,
                "days_until_expiry": max(0, days_until),
                "alert_level": alert_level,
            }
        )

    return alerts


async def mark_expired_permits(db: AsyncSession, building_id: UUID) -> int:
    """Auto-mark expired permits. Returns count of updates."""
    now = datetime.now(UTC)

    result = await db.execute(
        select(Permit).where(
            (Permit.building_id == building_id)
            & (Permit.expiry_date <= now)
            & (Permit.status != PermitStatus.EXPIRED)
            & (Permit.status != PermitStatus.REVOKED)
        )
    )
    expired_permits = result.scalars().all()

    count = 0
    for permit in expired_permits:
        permit.status = PermitStatus.EXPIRED
        permit.updated_at = datetime.now(UTC)
        count += 1

    if count > 0:
        await db.flush()
        logger.info("Marked %d permits as expired for building %s", count, building_id)

    return count
