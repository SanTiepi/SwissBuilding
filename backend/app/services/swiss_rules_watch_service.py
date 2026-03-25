"""SwissRules Watch — service layer."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.communal_adapter import CommunalAdapterProfile
from app.models.communal_override import CommunalRuleOverride
from app.models.rule_change_event import RuleChangeEvent
from app.models.swiss_rules_source import RuleSource

# Freshness thresholds per watch_tier (days)
_FRESHNESS_THRESHOLDS: dict[str, dict[str, int]] = {
    "daily": {"current": 1, "aging": 3, "stale": 7},
    "weekly": {"current": 7, "aging": 14, "stale": 30},
    "monthly": {"current": 30, "aging": 45, "stale": 90},
    "quarterly": {"current": 90, "aging": 120, "stale": 180},
}


def _compute_freshness(watch_tier: str, last_checked_at: datetime | None) -> str:
    if not last_checked_at:
        return "unknown"
    thresholds = _FRESHNESS_THRESHOLDS.get(watch_tier, _FRESHNESS_THRESHOLDS["weekly"])
    now = datetime.now(UTC)
    # Ensure last_checked_at is timezone-aware for subtraction
    if last_checked_at.tzinfo is None:
        last_checked_at = last_checked_at.replace(tzinfo=UTC)
    age_days = (now - last_checked_at).days
    if age_days <= thresholds["current"]:
        return "current"
    if age_days <= thresholds["aging"]:
        return "aging"
    if age_days <= thresholds["stale"]:
        return "stale"
    return "stale"


async def list_sources(
    db: AsyncSession,
    *,
    tier_filter: str | None = None,
    active_only: bool = True,
) -> list[RuleSource]:
    query = select(RuleSource)
    if active_only:
        query = query.where(RuleSource.is_active.is_(True))
    if tier_filter:
        query = query.where(RuleSource.watch_tier == tier_filter)
    query = query.order_by(RuleSource.source_code)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_source(db: AsyncSession, source_id: UUID) -> RuleSource | None:
    result = await db.execute(select(RuleSource).where(RuleSource.id == source_id))
    return result.scalar_one_or_none()


async def refresh_source_freshness(db: AsyncSession, source_id: UUID) -> RuleSource | None:
    source = await get_source(db, source_id)
    if not source:
        return None
    now = datetime.now(UTC)
    source.last_checked_at = now
    source.freshness_state = _compute_freshness(source.watch_tier, now)
    await db.flush()
    await db.refresh(source)
    return source


async def record_change_event(
    db: AsyncSession,
    source_id: UUID,
    event_data: dict,
) -> RuleChangeEvent:
    event = RuleChangeEvent(source_id=source_id, **event_data)
    db.add(event)
    # Update source last_changed_at
    source = await get_source(db, source_id)
    if source:
        now = datetime.now(UTC)
        source.last_changed_at = now
        # Append event_type to change_types_detected
        detected = source.change_types_detected or []
        et = event_data.get("event_type", "")
        if et and et not in detected:
            source.change_types_detected = [*detected, et]
    await db.flush()
    await db.refresh(event)
    return event


async def review_change_event(
    db: AsyncSession,
    event_id: UUID,
    user_id: UUID,
    notes: str | None = None,
) -> RuleChangeEvent | None:
    result = await db.execute(select(RuleChangeEvent).where(RuleChangeEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return None
    event.reviewed = True
    event.reviewed_by_user_id = user_id
    event.reviewed_at = datetime.now(UTC)
    event.review_notes = notes
    await db.flush()
    await db.refresh(event)
    return event


async def get_unreviewed_changes(db: AsyncSession) -> list[RuleChangeEvent]:
    query = (
        select(RuleChangeEvent).where(RuleChangeEvent.reviewed.is_(False)).order_by(RuleChangeEvent.detected_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_change_events(
    db: AsyncSession,
    *,
    source_id: UUID | None = None,
) -> list[RuleChangeEvent]:
    query = select(RuleChangeEvent)
    if source_id:
        query = query.where(RuleChangeEvent.source_id == source_id)
    query = query.order_by(RuleChangeEvent.detected_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


# ---- Commune Adapters ----


async def list_communal_adapters(
    db: AsyncSession,
    *,
    canton_filter: str | None = None,
) -> list[CommunalAdapterProfile]:
    query = select(CommunalAdapterProfile)
    if canton_filter:
        query = query.where(CommunalAdapterProfile.canton_code == canton_filter)
    query = query.order_by(CommunalAdapterProfile.commune_name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_commune_adapter(
    db: AsyncSession,
    commune_code: str,
) -> CommunalAdapterProfile | None:
    result = await db.execute(select(CommunalAdapterProfile).where(CommunalAdapterProfile.commune_code == commune_code))
    return result.scalar_one_or_none()


async def get_commune_overrides(
    db: AsyncSession,
    commune_code: str,
) -> list[CommunalRuleOverride]:
    query = (
        select(CommunalRuleOverride)
        .where(CommunalRuleOverride.commune_code == commune_code)
        .where(CommunalRuleOverride.is_active.is_(True))
        .order_by(CommunalRuleOverride.override_type)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_building_commune_context(db: AsyncSession, building_id: UUID) -> dict | None:
    """Return commune adapter + overrides applicable to a building based on its city/canton."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    city = building.city
    canton = building.canton

    # Try to find adapter by commune_name match (case-insensitive)
    adapter_result = await db.execute(
        select(CommunalAdapterProfile).where(
            CommunalAdapterProfile.canton_code == canton,
            CommunalAdapterProfile.commune_name.ilike(city),
        )
    )
    adapter = adapter_result.scalar_one_or_none()

    # Get overrides for the canton + city
    overrides_q = (
        select(CommunalRuleOverride)
        .where(
            CommunalRuleOverride.canton_code == canton,
            CommunalRuleOverride.is_active.is_(True),
        )
        .order_by(CommunalRuleOverride.override_type)
    )
    # If adapter found, match by commune_code; otherwise match by broad canton
    if adapter:
        overrides_q = overrides_q.where(CommunalRuleOverride.commune_code == adapter.commune_code)
    else:
        # Fallback: no adapter, no commune-specific overrides
        overrides_q = overrides_q.where(CommunalRuleOverride.commune_code == "__none__")

    overrides_result = await db.execute(overrides_q)
    overrides = list(overrides_result.scalars().all())

    return {
        "building_id": building_id,
        "city": city,
        "canton": canton,
        "adapter": adapter,
        "overrides": overrides,
    }
