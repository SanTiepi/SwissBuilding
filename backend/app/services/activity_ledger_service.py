"""Activity Ledger Service — record and verify building activity chains.

Provides tamper-evident logging of all significant building actions with
SHA-256 hash chain integrity verification.
"""

import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_activity import BuildingActivity

logger = logging.getLogger(__name__)


async def record_activity(
    db: AsyncSession,
    *,
    building_id: UUID,
    actor_id: UUID,
    actor_role: str,
    actor_name: str,
    activity_type: str,
    entity_type: str,
    entity_id: UUID,
    title: str,
    description: str | None = None,
    reason: str | None = None,
    metadata: dict | None = None,
) -> BuildingActivity:
    """Record a new activity entry with hash chain linkage.

    Fetches the last activity for the building, uses its activity_hash as
    previous_hash, then computes a new SHA-256 hash for tamper-evidence.
    """
    # Fetch last activity hash for this building
    result = await db.execute(
        select(BuildingActivity.activity_hash)
        .where(BuildingActivity.building_id == building_id)
        .order_by(BuildingActivity.created_at.desc())
        .limit(1)
    )
    last_hash = result.scalar_one_or_none()

    now = datetime.now(UTC)
    activity_hash = _compute_hash(
        actor_id=actor_id,
        activity_type=activity_type,
        entity_id=entity_id,
        timestamp=now,
        previous_hash=last_hash,
    )

    activity = BuildingActivity(
        building_id=building_id,
        actor_id=actor_id,
        actor_role=actor_role,
        actor_name=actor_name,
        activity_type=activity_type,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        description=description,
        reason=reason,
        metadata_json=metadata,
        previous_hash=last_hash,
        activity_hash=activity_hash,
        created_at=now,
    )
    db.add(activity)
    return activity


async def get_building_ledger(
    db: AsyncSession,
    building_id: UUID,
    *,
    page: int = 1,
    size: int = 50,
    actor_id: UUID | None = None,
    activity_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[BuildingActivity], int]:
    """Return paginated, filterable activity log for a building.

    Returns (items, total_count).
    """
    base = select(BuildingActivity).where(BuildingActivity.building_id == building_id)
    count_q = select(func.count()).select_from(BuildingActivity).where(BuildingActivity.building_id == building_id)

    if actor_id is not None:
        base = base.where(BuildingActivity.actor_id == actor_id)
        count_q = count_q.where(BuildingActivity.actor_id == actor_id)
    if activity_type is not None:
        base = base.where(BuildingActivity.activity_type == activity_type)
        count_q = count_q.where(BuildingActivity.activity_type == activity_type)
    if date_from is not None:
        base = base.where(BuildingActivity.created_at >= date_from)
        count_q = count_q.where(BuildingActivity.created_at >= date_from)
    if date_to is not None:
        base = base.where(BuildingActivity.created_at <= date_to)
        count_q = count_q.where(BuildingActivity.created_at <= date_to)

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * size
    items_q = base.order_by(BuildingActivity.created_at.desc()).offset(offset).limit(size)
    items_result = await db.execute(items_q)
    items = list(items_result.scalars().all())

    return items, total


async def verify_chain_integrity(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Walk the full chain for a building and verify all hashes.

    Returns {"valid": bool, "total_entries": int, "first_break_at": int | None}.
    """
    result = await db.execute(
        select(BuildingActivity)
        .where(BuildingActivity.building_id == building_id)
        .order_by(BuildingActivity.created_at.asc())
    )
    entries = list(result.scalars().all())

    if not entries:
        return {"valid": True, "total_entries": 0, "first_break_at": None}

    previous_hash: str | None = None
    for idx, entry in enumerate(entries):
        # Check previous_hash linkage
        if entry.previous_hash != previous_hash:
            return {"valid": False, "total_entries": len(entries), "first_break_at": idx}

        # Recompute and verify activity_hash
        expected = _compute_hash(
            actor_id=entry.actor_id,
            activity_type=entry.activity_type,
            entity_id=entry.entity_id,
            timestamp=entry.created_at,
            previous_hash=entry.previous_hash,
        )
        if entry.activity_hash != expected:
            return {"valid": False, "total_entries": len(entries), "first_break_at": idx}

        previous_hash = entry.activity_hash

    return {"valid": True, "total_entries": len(entries), "first_break_at": None}


def _compute_hash(
    *,
    actor_id: UUID,
    activity_type: str,
    entity_id: UUID,
    timestamp: datetime,
    previous_hash: str | None,
) -> str:
    """Compute SHA-256 hash for a single activity entry."""
    payload = f"{actor_id}|{activity_type}|{entity_id}|{timestamp.isoformat()}|{previous_hash or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
