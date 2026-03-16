"""
SwissBuildingOS - Notification Digest Service

Aggregates recent notifications, action items, compliance deadlines,
and change signals into a structured daily or weekly digest.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.change_signal import ChangeSignal
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.notification import Notification
from app.schemas.notification_digest import (
    DigestMetrics,
    DigestPreview,
    DigestSection,
    NotificationDigest,
)


def _period_window(period: str) -> tuple[datetime, datetime]:
    """Return (start, end) for the given period ending now."""
    now = datetime.now(UTC)
    if period == "weekly":
        start = now - timedelta(days=7)
    else:
        start = now - timedelta(days=1)
    return start, now


async def get_user_building_ids(db: AsyncSession, user_id: UUID) -> list[UUID]:
    """Find buildings a user has access to via created_by or assignments."""
    # Buildings created by user
    result = await db.execute(select(Building.id).where(Building.created_by == user_id))
    building_ids = set(result.scalars().all())

    # Buildings assigned to user
    result = await db.execute(
        select(Assignment.target_id).where(
            Assignment.user_id == user_id,
            Assignment.target_type == "building",
        )
    )
    building_ids.update(result.scalars().all())

    return list(building_ids)


async def get_overdue_actions(db: AsyncSession, user_id: UUID) -> list[dict]:
    """Return overdue action items for the user's buildings."""
    building_ids = await get_user_building_ids(db, user_id)
    if not building_ids:
        return []

    today = date.today()
    result = await db.execute(
        select(ActionItem).where(
            ActionItem.building_id.in_(building_ids),
            ActionItem.status.in_(["open", "in_progress"]),
            ActionItem.due_date.isnot(None),
            ActionItem.due_date < today,
        )
    )
    actions = result.scalars().all()

    return [
        {
            "title": a.title,
            "description": a.description or "",
            "priority": a.priority,
            "resource_type": "action_item",
            "resource_id": str(a.id),
            "timestamp": a.due_date.isoformat() if a.due_date else None,
        }
        for a in actions
    ]


async def _build_urgent_actions_section(db: AsyncSession, building_ids: list[UUID], now: datetime) -> DigestSection:
    """Actions with priority=high due within 7 days or overdue."""
    if not building_ids:
        return DigestSection(title="Urgent actions", items=[], count=0)

    today = now.date() if isinstance(now, datetime) else now
    soon = today + timedelta(days=7)

    result = await db.execute(
        select(ActionItem).where(
            ActionItem.building_id.in_(building_ids),
            ActionItem.status.in_(["open", "in_progress"]),
            ActionItem.priority == "high",
            ActionItem.due_date.isnot(None),
            ActionItem.due_date <= soon,
        )
    )
    actions = result.scalars().all()

    items = sorted(
        [
            {
                "title": a.title,
                "description": a.description or "",
                "priority": a.priority,
                "resource_type": "action_item",
                "resource_id": str(a.id),
                "timestamp": a.due_date.isoformat() if a.due_date else None,
            }
            for a in actions
        ],
        key=lambda x: x["timestamp"] or "",
    )

    return DigestSection(title="Urgent actions", items=items, count=len(items))


async def _build_notifications_section(db: AsyncSession, user_id: UUID, period_start: datetime) -> DigestSection:
    """Unread notifications from the period."""
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.status == "unread",
            Notification.created_at >= period_start,
        )
    )
    notifications = result.scalars().all()

    items = sorted(
        [
            {
                "title": n.title,
                "description": n.body or "",
                "priority": "normal",
                "resource_type": "notification",
                "resource_id": str(n.id),
                "timestamp": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        key=lambda x: x["timestamp"] or "",
        reverse=True,
    )

    return DigestSection(title="Recent notifications", items=items, count=len(items))


async def _build_deadlines_section(db: AsyncSession, building_ids: list[UUID]) -> DigestSection:
    """Compliance deadlines within 30 days for the user's buildings.

    Uses action items with source_type containing 'compliance' or 'deadline'
    as a lightweight proxy — avoids coupling to the full compliance timeline engine.
    """
    if not building_ids:
        return DigestSection(title="Upcoming deadlines", items=[], count=0)

    today = date.today()
    horizon = today + timedelta(days=30)

    result = await db.execute(
        select(ActionItem).where(
            ActionItem.building_id.in_(building_ids),
            ActionItem.status.in_(["open", "in_progress"]),
            ActionItem.due_date.isnot(None),
            ActionItem.due_date >= today,
            ActionItem.due_date <= horizon,
        )
    )
    actions = result.scalars().all()

    items = sorted(
        [
            {
                "title": a.title,
                "description": a.description or "",
                "priority": a.priority,
                "resource_type": "action_item",
                "resource_id": str(a.id),
                "timestamp": a.due_date.isoformat() if a.due_date else None,
            }
            for a in actions
        ],
        key=lambda x: x["timestamp"] or "",
    )

    return DigestSection(title="Upcoming deadlines", items=items, count=len(items))


async def _build_signals_section(db: AsyncSession, building_ids: list[UUID], period_start: datetime) -> DigestSection:
    """Change signals detected during the period for the user's buildings."""
    if not building_ids:
        return DigestSection(title="New signals", items=[], count=0)

    result = await db.execute(
        select(ChangeSignal).where(
            ChangeSignal.building_id.in_(building_ids),
            ChangeSignal.detected_at >= period_start,
        )
    )
    signals = result.scalars().all()

    items = sorted(
        [
            {
                "title": s.title,
                "description": s.description or "",
                "priority": s.severity or "info",
                "resource_type": "change_signal",
                "resource_id": str(s.id),
                "timestamp": s.detected_at.isoformat() if s.detected_at else None,
            }
            for s in signals
        ],
        key=lambda x: x["timestamp"] or "",
        reverse=True,
    )

    return DigestSection(title="New signals", items=items, count=len(items))


async def _build_completed_section(db: AsyncSession, building_ids: list[UUID], period_start: datetime) -> DigestSection:
    """Interventions and diagnostics completed during the period."""
    items: list[dict] = []

    if building_ids:
        # Completed interventions
        result = await db.execute(
            select(Intervention).where(
                Intervention.building_id.in_(building_ids),
                Intervention.status == "completed",
                Intervention.updated_at >= period_start,
            )
        )
        for intv in result.scalars().all():
            items.append(
                {
                    "title": intv.title,
                    "description": intv.description or "",
                    "priority": "info",
                    "resource_type": "intervention",
                    "resource_id": str(intv.id),
                    "timestamp": intv.updated_at.isoformat() if intv.updated_at else None,
                }
            )

        # Completed diagnostics
        result = await db.execute(
            select(Diagnostic).where(
                Diagnostic.building_id.in_(building_ids),
                Diagnostic.status.in_(["completed", "validated"]),
                Diagnostic.updated_at >= period_start,
            )
        )
        for diag in result.scalars().all():
            items.append(
                {
                    "title": f"Diagnostic {diag.diagnostic_type}",
                    "description": diag.summary or "",
                    "priority": "info",
                    "resource_type": "diagnostic",
                    "resource_id": str(diag.id),
                    "timestamp": diag.updated_at.isoformat() if diag.updated_at else None,
                }
            )

    items.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return DigestSection(title="Completed work", items=items, count=len(items))


async def generate_digest(db: AsyncSession, user_id: UUID, period: str = "daily") -> NotificationDigest:
    """Generate a structured digest for a user."""
    period_start, period_end = _period_window(period)
    building_ids = await get_user_building_ids(db, user_id)

    # Build all sections
    urgent_section = await _build_urgent_actions_section(db, building_ids, period_end)
    notif_section = await _build_notifications_section(db, user_id, period_start)
    deadlines_section = await _build_deadlines_section(db, building_ids)
    signals_section = await _build_signals_section(db, building_ids, period_start)
    completed_section = await _build_completed_section(db, building_ids, period_start)

    sections = [
        urgent_section,
        notif_section,
        deadlines_section,
        signals_section,
        completed_section,
    ]

    # Compute metrics
    overdue_actions = await get_overdue_actions(db, user_id)

    metrics = DigestMetrics(
        total_notifications=notif_section.count,
        unread_count=notif_section.count,
        actions_due_soon=urgent_section.count,
        overdue_actions=len(overdue_actions),
        new_signals=signals_section.count,
        upcoming_deadlines=deadlines_section.count,
    )

    return NotificationDigest(
        user_id=user_id,
        period=period,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        sections=sections,
        generated_at=datetime.now(UTC),
    )


async def get_digest_preview(db: AsyncSession, user_id: UUID, period: str = "daily") -> DigestPreview:
    """Lightweight preview with headline and counts."""
    period_start, _ = _period_window(period)
    building_ids = await get_user_building_ids(db, user_id)

    # Count urgent actions
    today = date.today()
    soon = today + timedelta(days=7)
    urgent_count = 0
    if building_ids:
        result = await db.execute(
            select(ActionItem.id).where(
                ActionItem.building_id.in_(building_ids),
                ActionItem.status.in_(["open", "in_progress"]),
                ActionItem.priority == "high",
                ActionItem.due_date.isnot(None),
                ActionItem.due_date <= soon,
            )
        )
        urgent_count = len(result.all())

    # Count overdue
    overdue_count = len(await get_overdue_actions(db, user_id))

    # Count new signals
    signal_count = 0
    if building_ids:
        result = await db.execute(
            select(ChangeSignal.id).where(
                ChangeSignal.building_id.in_(building_ids),
                ChangeSignal.detected_at >= period_start,
            )
        )
        signal_count = len(result.all())

    # Count unread notifications
    result = await db.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.status == "unread",
            Notification.created_at >= period_start,
        )
    )
    notif_count = len(result.all())

    total = urgent_count + overdue_count + signal_count + notif_count
    has_urgent = urgent_count > 0 or overdue_count > 0

    # Build headline
    parts: list[str] = []
    if urgent_count + overdue_count > 0:
        parts.append(f"{urgent_count + overdue_count} actions due")
    if signal_count > 0:
        parts.append(f"{signal_count} new signals")
    if notif_count > 0:
        parts.append(f"{notif_count} notifications")

    headline = ", ".join(parts) if parts else "No new activity"

    return DigestPreview(
        user_id=user_id,
        period=period,
        headline=headline,
        has_urgent=has_urgent,
        total_items=total,
    )


async def mark_digest_sent(db: AsyncSession, user_id: UUID, period: str = "daily") -> None:
    """Mark digest as sent by marking all included notifications as read."""
    period_start, _ = _period_window(period)
    now = datetime.now(UTC)

    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.status == "unread",
            Notification.created_at >= period_start,
        )
        .values(status="read", read_at=now)
    )
    await db.commit()
