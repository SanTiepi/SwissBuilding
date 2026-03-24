"""BatiConnect — Obligation operations service."""

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.obligation import Obligation

# Recurrence → timedelta mapping
_RECURRENCE_DELTAS: dict[str, timedelta | None] = {
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=91),
    "semi_annual": timedelta(days=182),
    "annual": timedelta(days=365),
    "biennial": timedelta(days=730),
    "five_yearly": timedelta(days=1826),
}


def _calculate_status(due_date: date, completed_at: datetime | None, reminder_days: int = 30) -> str:
    """Auto-calculate status from due_date vs today."""
    if completed_at is not None:
        return "completed"
    today = date.today()
    if due_date < today:
        return "overdue"
    if due_date <= today + timedelta(days=reminder_days):
        return "due_soon"
    return "upcoming"


async def create_obligation(db: AsyncSession, building_id: UUID, data: dict) -> Obligation:
    """Create an obligation with auto-calculated status."""
    reminder_days = data.get("reminder_days_before", 30)
    status = _calculate_status(data["due_date"], None, reminder_days)
    obligation = Obligation(building_id=building_id, status=status, **data)
    db.add(obligation)
    await db.flush()
    await db.refresh(obligation)
    return obligation


async def list_obligations(
    db: AsyncSession,
    building_id: UUID,
    *,
    status_filter: str | None = None,
    obligation_type: str | None = None,
) -> list[Obligation]:
    """List obligations for a building, optionally filtered."""
    query = select(Obligation).where(Obligation.building_id == building_id)
    if status_filter:
        query = query.where(Obligation.status == status_filter)
    if obligation_type:
        query = query.where(Obligation.obligation_type == obligation_type)
    query = query.order_by(Obligation.due_date.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_obligation(db: AsyncSession, obligation_id: UUID) -> Obligation | None:
    result = await db.execute(select(Obligation).where(Obligation.id == obligation_id))
    return result.scalar_one_or_none()


async def get_due_soon(db: AsyncSession, building_id: UUID, days: int = 30) -> list[Obligation]:
    """Get obligations due within N days (not completed/cancelled)."""
    threshold = date.today() + timedelta(days=days)
    query = (
        select(Obligation)
        .where(
            Obligation.building_id == building_id,
            Obligation.due_date <= threshold,
            Obligation.due_date >= date.today(),
            Obligation.status.notin_(["completed", "cancelled"]),
        )
        .order_by(Obligation.due_date.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_overdue(db: AsyncSession, building_id: UUID) -> list[Obligation]:
    """Get overdue obligations (not completed/cancelled)."""
    query = (
        select(Obligation)
        .where(
            Obligation.building_id == building_id,
            Obligation.due_date < date.today(),
            Obligation.status.notin_(["completed", "cancelled"]),
        )
        .order_by(Obligation.due_date.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_obligation(db: AsyncSession, obligation: Obligation, data: dict) -> Obligation:
    """Update obligation fields and recalculate status if due_date changed."""
    for key, value in data.items():
        setattr(obligation, key, value)
    # Recalculate status if not manually completed/cancelled
    if obligation.status not in ("completed", "cancelled"):
        obligation.status = _calculate_status(
            obligation.due_date, obligation.completed_at, obligation.reminder_days_before or 30
        )
    await db.flush()
    await db.refresh(obligation)
    return obligation


async def complete_obligation(
    db: AsyncSession, obligation: Obligation, user_id: UUID, notes: str | None = None
) -> tuple[Obligation, Obligation | None]:
    """Mark obligation as completed. If recurring, generate next instance.

    Returns (completed_obligation, next_obligation_or_None).
    """
    obligation.status = "completed"
    obligation.completed_at = datetime.utcnow()
    obligation.completed_by_user_id = user_id
    if notes:
        obligation.notes = notes
    await db.flush()
    await db.refresh(obligation)

    next_obligation = None
    if obligation.recurrence and obligation.recurrence in _RECURRENCE_DELTAS:
        delta = _RECURRENCE_DELTAS[obligation.recurrence]
        next_due = obligation.due_date + delta
        next_status = _calculate_status(next_due, None, obligation.reminder_days_before or 30)
        next_obligation = Obligation(
            building_id=obligation.building_id,
            title=obligation.title,
            description=obligation.description,
            obligation_type=obligation.obligation_type,
            due_date=next_due,
            recurrence=obligation.recurrence,
            status=next_status,
            priority=obligation.priority,
            responsible_org_id=obligation.responsible_org_id,
            responsible_user_id=obligation.responsible_user_id,
            linked_entity_type=obligation.linked_entity_type,
            linked_entity_id=obligation.linked_entity_id,
            reminder_days_before=obligation.reminder_days_before,
        )
        db.add(next_obligation)
        await db.flush()
        await db.refresh(next_obligation)

    return obligation, next_obligation


async def cancel_obligation(db: AsyncSession, obligation: Obligation) -> Obligation:
    """Cancel an obligation."""
    obligation.status = "cancelled"
    await db.flush()
    await db.refresh(obligation)
    return obligation


async def refresh_statuses(db: AsyncSession, building_id: UUID) -> int:
    """Refresh statuses for all active obligations of a building. Returns count updated."""
    obligations = await list_obligations(db, building_id)
    updated = 0
    for obl in obligations:
        if obl.status in ("completed", "cancelled"):
            continue
        new_status = _calculate_status(obl.due_date, obl.completed_at, obl.reminder_days_before or 30)
        if new_status != obl.status:
            obl.status = new_status
            updated += 1
    if updated:
        await db.flush()
    return updated
