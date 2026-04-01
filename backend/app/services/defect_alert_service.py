"""BatiConnect — DefectShield alert service: notification triggers for defect timelines.

Listens to DefectTimeline status changes and deadline proximity.
Creates Notification records when:
- Deadline approaching (7 days — warning level)
- Deadline missed / expired (critical level)
- Defect resolved

Deduplication: identical alert (type + defect_id) not duplicated
if an unread notification already exists.

Respects user notification preferences (type enabled, channel, quiet hours).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.defect_timeline import DefectTimeline
from app.models.notification import Notification

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALERT_TYPE_DEADLINE_APPROACHING = "defect_deadline_approaching"
ALERT_TYPE_DEADLINE_MISSED = "defect_deadline_missed"
ALERT_TYPE_DEFECT_RESOLVED = "defect_resolved"

APPROACHING_THRESHOLD_DAYS = 7  # Art. 367 CO — warn 7 days before deadline

NOTIFICATION_TYPE = "system"  # reuses existing notification type


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _make_fingerprint(alert_type: str, defect_id: UUID) -> str:
    return f"defect:{alert_type}:{defect_id}"


async def _notification_exists(
    db: AsyncSession,
    user_id: UUID,
    alert_type: str,
    defect_id: UUID,
) -> bool:
    """Check if an unread notification with same fingerprint exists."""
    fingerprint = _make_fingerprint(alert_type, defect_id)
    result = await db.execute(
        select(func.count()).where(
            and_(
                Notification.user_id == user_id,
                Notification.status == "unread",
                Notification.link == fingerprint,
            )
        )
    )
    return (result.scalar() or 0) > 0


# ---------------------------------------------------------------------------
# Preference check
# ---------------------------------------------------------------------------


async def _should_notify_user(
    db: AsyncSession,
    user_id: UUID,
) -> bool:
    """Check user notification preferences. Returns True if notification should be sent."""
    try:
        from app.services.notification_preferences_service import should_notify

        return await should_notify(db, user_id, NOTIFICATION_TYPE, channel="in_app")
    except Exception:
        # If preferences service fails, default to sending the notification
        logger.debug("Notification preferences check failed, defaulting to notify")
        return True


# ---------------------------------------------------------------------------
# Alert creators
# ---------------------------------------------------------------------------


def _build_details(
    timeline: DefectTimeline,
    *,
    days_remaining: int | None = None,
) -> dict:
    """Build structured details dict for a defect alert notification."""
    details: dict = {
        "building_id": str(timeline.building_id),
        "defect_type": timeline.defect_type,
        "deadline_date": timeline.notification_deadline.isoformat(),
    }
    if days_remaining is not None:
        details["days_remaining"] = days_remaining
    return details


async def _create_alert(
    db: AsyncSession,
    user_id: UUID,
    alert_type: str,
    title: str,
    body: str,
    defect_id: UUID,
    timeline: DefectTimeline,
    *,
    days_remaining: int | None = None,
) -> Notification | None:
    """Create a notification if no duplicate unread exists and user preferences allow it.

    Returns None if deduplicated or preferences block delivery.
    """
    if not await _should_notify_user(db, user_id):
        return None

    if await _notification_exists(db, user_id, alert_type, defect_id):
        return None

    details = _build_details(timeline, days_remaining=days_remaining)

    notification = Notification(
        user_id=user_id,
        type=NOTIFICATION_TYPE,
        title=title,
        body=body,
        link=_make_fingerprint(alert_type, defect_id),
        status="unread",
    )
    db.add(notification)
    logger.info(
        "Defect alert created: type=%s building=%s defect_type=%s deadline=%s",
        alert_type,
        details["building_id"],
        details["defect_type"],
        details["deadline_date"],
    )
    return notification


# ---------------------------------------------------------------------------
# Status-change triggers
# ---------------------------------------------------------------------------


async def on_status_change(
    db: AsyncSession,
    timeline: DefectTimeline,
    new_status: str,
    user_id: UUID,
) -> Notification | None:
    """Trigger notification on DefectTimeline status transition.

    Called after update_defect_status succeeds.
    Fires on:
    - "expired" -> deadline missed alert (critical)
    - "resolved" -> defect resolved alert
    """
    if new_status == "expired":
        return await _create_alert(
            db,
            user_id=user_id,
            alert_type=ALERT_TYPE_DEADLINE_MISSED,
            title=f"Delai de notification depasse — {timeline.defect_type}",
            body=(
                f"Le delai de notification (Art. 367 CO) pour le defaut "
                f"'{timeline.defect_type}' est echu depuis le "
                f"{timeline.notification_deadline.isoformat()}."
            ),
            defect_id=timeline.id,
            timeline=timeline,
        )

    if new_status == "resolved":
        return await _create_alert(
            db,
            user_id=user_id,
            alert_type=ALERT_TYPE_DEFECT_RESOLVED,
            title=f"Defaut resolu — {timeline.defect_type}",
            body=(f"Le defaut '{timeline.defect_type}' a ete marque comme resolu."),
            defect_id=timeline.id,
            timeline=timeline,
        )

    return None


# ---------------------------------------------------------------------------
# Post-create check
# ---------------------------------------------------------------------------


async def check_deadline_on_create(
    db: AsyncSession,
    timeline: DefectTimeline,
    user_id: UUID,
) -> Notification | None:
    """Check if a newly created timeline already has an approaching or passed deadline.

    Called right after create_timeline to immediately alert if needed.
    """
    today = date.today()
    days_remaining = (timeline.notification_deadline - today).days

    if days_remaining < 0:
        # Already expired
        return await _create_alert(
            db,
            user_id=user_id,
            alert_type=ALERT_TYPE_DEADLINE_MISSED,
            title=f"Delai de notification depasse — {timeline.defect_type}",
            body=(
                f"Le delai de notification (Art. 367 CO) pour le defaut "
                f"'{timeline.defect_type}' est echu depuis le "
                f"{timeline.notification_deadline.isoformat()}."
            ),
            defect_id=timeline.id,
            timeline=timeline,
            days_remaining=days_remaining,
        )

    if days_remaining <= APPROACHING_THRESHOLD_DAYS:
        # Within 7 days — warning
        return await _create_alert(
            db,
            user_id=user_id,
            alert_type=ALERT_TYPE_DEADLINE_APPROACHING,
            title=f"Delai de notification dans {days_remaining} jour(s) — {timeline.defect_type}",
            body=(
                f"Le delai de notification (Art. 367 CO) pour le defaut "
                f"'{timeline.defect_type}' expire le {timeline.notification_deadline.isoformat()} "
                f"({days_remaining} jour(s) restant(s))."
            ),
            defect_id=timeline.id,
            timeline=timeline,
            days_remaining=days_remaining,
        )

    return None


# ---------------------------------------------------------------------------
# Deadline-approaching scanner
# ---------------------------------------------------------------------------


async def scan_approaching_deadlines(
    db: AsyncSession,
    user_id: UUID,
    threshold_days: int = APPROACHING_THRESHOLD_DAYS,
    building_id: UUID | None = None,
) -> list[Notification]:
    """Scan active defect timelines and create alerts for approaching deadlines.

    Creates one notification per approaching defect (deduplicated).

    Args:
        db: Database session.
        user_id: User to notify.
        threshold_days: Number of days before deadline to trigger alert (default 7).
        building_id: Optional filter by building.

    Returns:
        List of newly created Notification objects.
    """
    today = date.today()
    threshold_date = today + timedelta(days=threshold_days)

    query = select(DefectTimeline).where(
        DefectTimeline.status == "active",
        DefectTimeline.notification_deadline <= threshold_date,
        DefectTimeline.notification_deadline >= today,
    )
    if building_id:
        query = query.where(DefectTimeline.building_id == building_id)

    query = query.order_by(DefectTimeline.notification_deadline.asc())
    result = await db.execute(query)
    timelines = list(result.scalars().all())

    created: list[Notification] = []
    for t in timelines:
        days_remaining = (t.notification_deadline - today).days
        notification = await _create_alert(
            db,
            user_id=user_id,
            alert_type=ALERT_TYPE_DEADLINE_APPROACHING,
            title=f"Delai de notification dans {days_remaining} jour(s) — {t.defect_type}",
            body=(
                f"Le delai de notification (Art. 367 CO) pour le defaut "
                f"'{t.defect_type}' expire le {t.notification_deadline.isoformat()} "
                f"({days_remaining} jour(s) restant(s))."
            ),
            defect_id=t.id,
            timeline=t,
            days_remaining=days_remaining,
        )
        if notification:
            created.append(notification)

    if created:
        await db.flush()

    return created


# ---------------------------------------------------------------------------
# Expired scanner (detect + alert)
# ---------------------------------------------------------------------------


async def scan_and_expire(
    db: AsyncSession,
    user_id: UUID,
) -> list[Notification]:
    """Detect expired defect timelines and create missed-deadline alerts.

    Marks active timelines past their deadline as "expired" and sends
    a notification for each.

    Returns:
        List of newly created Notification objects for expired timelines.
    """
    today = date.today()
    result = await db.execute(
        select(DefectTimeline).where(
            DefectTimeline.status == "active",
            DefectTimeline.notification_deadline < today,
        )
    )
    expired = list(result.scalars().all())

    created: list[Notification] = []
    for t in expired:
        t.status = "expired"
        notification = await _create_alert(
            db,
            user_id=user_id,
            alert_type=ALERT_TYPE_DEADLINE_MISSED,
            title=f"Delai de notification depasse — {t.defect_type}",
            body=(
                f"Le delai de notification (Art. 367 CO) pour le defaut "
                f"'{t.defect_type}' est echu depuis le "
                f"{t.notification_deadline.isoformat()}."
            ),
            defect_id=t.id,
            timeline=t,
        )
        if notification:
            created.append(notification)

    if expired:
        await db.commit()

    return created
