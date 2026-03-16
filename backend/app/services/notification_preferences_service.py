"""
SwissBuildingOS - Extended Notification Preferences Service

Provides channel routing, quiet hours, and per-type granularity
on top of the existing basic notification preferences.
"""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationPreferenceExtended
from app.schemas.notification_preferences import (
    FullNotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationTypePreference,
    QuietHours,
)

NOTIFICATION_TYPES = ["action", "invitation", "export", "system"]


def _default_type_preferences() -> list[NotificationTypePreference]:
    return [NotificationTypePreference(type=t, channels=["in_app"], enabled=True) for t in NOTIFICATION_TYPES]


def _default_quiet_hours() -> QuietHours:
    return QuietHours()


def _serialize_preferences(prefs: FullNotificationPreferences) -> str:
    return json.dumps(
        {
            "type_preferences": [tp.model_dump() for tp in prefs.type_preferences],
            "quiet_hours": prefs.quiet_hours.model_dump(),
            "digest_frequency": prefs.digest_frequency,
        }
    )


def _deserialize_preferences(user_id: UUID, raw: str, updated_at: datetime | None) -> FullNotificationPreferences:
    data = json.loads(raw)
    return FullNotificationPreferences(
        user_id=user_id,
        type_preferences=[NotificationTypePreference(**tp) for tp in data.get("type_preferences", [])],
        quiet_hours=QuietHours(**data.get("quiet_hours", {})),
        digest_frequency=data.get("digest_frequency", "never"),
        updated_at=updated_at,
    )


async def get_full_preferences(db: AsyncSession, user_id: UUID) -> FullNotificationPreferences:
    """Return user's full preferences, creating defaults if none exist."""
    result = await db.execute(
        select(NotificationPreferenceExtended).where(NotificationPreferenceExtended.user_id == user_id)
    )
    row = result.scalar_one_or_none()

    if row is None:
        prefs = FullNotificationPreferences(
            user_id=user_id,
            type_preferences=_default_type_preferences(),
            quiet_hours=_default_quiet_hours(),
            digest_frequency="never",
            updated_at=None,
        )
        ext = NotificationPreferenceExtended(
            user_id=user_id,
            preferences_json=_serialize_preferences(prefs),
        )
        db.add(ext)
        await db.commit()
        await db.refresh(ext)
        prefs.updated_at = ext.updated_at
        return prefs

    return _deserialize_preferences(user_id, row.preferences_json, row.updated_at)


async def update_preferences(
    db: AsyncSession, user_id: UUID, data: NotificationPreferencesUpdate
) -> FullNotificationPreferences:
    """Merge partial update into existing preferences."""
    current = await get_full_preferences(db, user_id)

    update_data = data.model_dump(exclude_unset=True)

    if "type_preferences" in update_data:
        current.type_preferences = [NotificationTypePreference(**tp) for tp in update_data["type_preferences"]]
    if "quiet_hours" in update_data:
        current.quiet_hours = QuietHours(**update_data["quiet_hours"])
    if "digest_frequency" in update_data:
        current.digest_frequency = update_data["digest_frequency"]

    result = await db.execute(
        select(NotificationPreferenceExtended).where(NotificationPreferenceExtended.user_id == user_id)
    )
    row = result.scalar_one()
    row.preferences_json = _serialize_preferences(current)
    await db.commit()
    await db.refresh(row)
    current.updated_at = row.updated_at
    return current


def _is_in_quiet_hours(now_hour: int, start_hour: int, end_hour: int) -> bool:
    """Check if current hour falls within quiet hours window."""
    if start_hour <= end_hour:
        # e.g., 9-17: quiet during daytime
        return start_hour <= now_hour < end_hour
    else:
        # e.g., 22-7: quiet overnight (wraps midnight)
        return now_hour >= start_hour or now_hour < end_hour


async def should_notify(
    db: AsyncSession,
    user_id: UUID,
    notification_type: str,
    channel: str = "in_app",
    now_hour: int | None = None,
) -> bool:
    """Check if a notification should be delivered based on preferences + quiet hours.

    System notifications always bypass quiet hours.
    The now_hour parameter allows testing without timezone dependency.
    """
    prefs = await get_full_preferences(db, user_id)

    # Find type preference
    type_pref = None
    for tp in prefs.type_preferences:
        if tp.type == notification_type:
            type_pref = tp
            break

    # Unknown type: don't notify
    if type_pref is None:
        return False

    # Type disabled entirely
    if not type_pref.enabled:
        return False

    # Channel not enabled for this type
    if channel not in type_pref.channels:
        return False

    # Check quiet hours (system bypasses)
    if prefs.quiet_hours.enabled and notification_type != "system":
        if now_hour is None:
            try:
                import zoneinfo

                tz = zoneinfo.ZoneInfo(prefs.quiet_hours.timezone)
                now_hour = datetime.now(tz=tz).hour
            except Exception:
                now_hour = datetime.utcnow().hour

        if _is_in_quiet_hours(now_hour, prefs.quiet_hours.start_hour, prefs.quiet_hours.end_hour):
            return False

    return True


async def get_digest_candidates(db: AsyncSession) -> list[UUID]:
    """Return user_ids where digest is enabled (daily or weekly)."""
    result = await db.execute(select(NotificationPreferenceExtended))
    rows = result.scalars().all()

    candidates = []
    for row in rows:
        try:
            data = json.loads(row.preferences_json)
            freq = data.get("digest_frequency", "never")
            if freq in ("daily", "weekly"):
                candidates.append(row.user_id)
        except (json.JSONDecodeError, KeyError):
            continue

    return candidates
