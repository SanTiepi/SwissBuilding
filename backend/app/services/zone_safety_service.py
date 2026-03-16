"""Zone-level safety readiness and occupant notice service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone_safety import OccupantNotice, ZoneSafetyStatus
from app.schemas.zone_safety import (
    VALID_AUDIENCES,
    VALID_NOTICE_TYPES,
    VALID_SAFETY_LEVELS,
    VALID_SEVERITIES,
    OccupantNoticeCreate,
    ZoneSafetyStatusCreate,
)

# ---------------------------------------------------------------------------
# Zone Safety Status
# ---------------------------------------------------------------------------


async def assess_zone_safety(
    db: AsyncSession,
    zone_id: UUID,
    building_id: UUID,
    data: ZoneSafetyStatusCreate,
    assessed_by: UUID | None = None,
) -> ZoneSafetyStatus:
    """Create a new safety assessment for a zone, marking previous ones as non-current."""
    if data.safety_level not in VALID_SAFETY_LEVELS:
        raise ValueError(f"Invalid safety_level '{data.safety_level}'. Must be one of {VALID_SAFETY_LEVELS}")

    # Mark previous current statuses as non-current
    await db.execute(
        update(ZoneSafetyStatus)
        .where(ZoneSafetyStatus.zone_id == zone_id, ZoneSafetyStatus.is_current.is_(True))
        .values(is_current=False)
    )

    status = ZoneSafetyStatus(
        zone_id=zone_id,
        building_id=building_id,
        safety_level=data.safety_level,
        restriction_type=data.restriction_type,
        hazard_types=data.hazard_types,
        assessed_by=assessed_by,
        assessment_notes=data.assessment_notes,
        valid_until=data.valid_until,
        is_current=True,
    )
    db.add(status)
    return status


async def get_zone_safety(db: AsyncSession, zone_id: UUID) -> ZoneSafetyStatus | None:
    """Get the current safety status for a zone."""
    result = await db.execute(
        select(ZoneSafetyStatus).where(
            ZoneSafetyStatus.zone_id == zone_id,
            ZoneSafetyStatus.is_current.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_building_safety_summary(db: AsyncSession, building_id: UUID) -> dict:
    """Get a summary of zone safety levels for a building."""
    result = await db.execute(
        select(ZoneSafetyStatus).where(
            ZoneSafetyStatus.building_id == building_id,
            ZoneSafetyStatus.is_current.is_(True),
        )
    )
    statuses = list(result.scalars().all())

    summary: dict[str, int] = {}
    for s in statuses:
        summary[s.safety_level] = summary.get(s.safety_level, 0) + 1

    return {
        "building_id": str(building_id),
        "total_zones_assessed": len(statuses),
        "by_safety_level": summary,
        "zones": [
            {
                "zone_id": str(s.zone_id),
                "safety_level": s.safety_level,
                "restriction_type": s.restriction_type,
                "hazard_types": s.hazard_types,
            }
            for s in statuses
        ],
    }


# ---------------------------------------------------------------------------
# Occupant Notices
# ---------------------------------------------------------------------------


async def create_notice(
    db: AsyncSession,
    building_id: UUID,
    data: OccupantNoticeCreate,
    created_by: UUID,
) -> OccupantNotice:
    """Create a draft occupant notice."""
    if data.notice_type not in VALID_NOTICE_TYPES:
        raise ValueError(f"Invalid notice_type '{data.notice_type}'. Must be one of {VALID_NOTICE_TYPES}")
    if data.severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity '{data.severity}'. Must be one of {VALID_SEVERITIES}")
    if data.audience not in VALID_AUDIENCES:
        raise ValueError(f"Invalid audience '{data.audience}'. Must be one of {VALID_AUDIENCES}")

    notice = OccupantNotice(
        building_id=building_id,
        zone_id=data.zone_id,
        notice_type=data.notice_type,
        severity=data.severity,
        title=data.title,
        body=data.body,
        audience=data.audience,
        expires_at=data.expires_at,
        created_by=created_by,
        status="draft",
    )
    db.add(notice)
    return notice


async def publish_notice(db: AsyncSession, notice_id: UUID) -> OccupantNotice:
    """Publish a draft notice."""
    notice = await _get_notice_or_raise(db, notice_id)
    if notice.status != "draft":
        raise ValueError(f"Cannot publish notice in status '{notice.status}'")
    notice.status = "published"
    notice.published_at = datetime.now(UTC)
    return notice


async def list_notices(
    db: AsyncSession,
    building_id: UUID,
    status: str | None = None,
) -> list[OccupantNotice]:
    """List notices for a building, optionally filtered by status."""
    query = select(OccupantNotice).where(OccupantNotice.building_id == building_id)
    if status is not None:
        query = query.where(OccupantNotice.status == status)
    query = query.order_by(OccupantNotice.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_active_notices(db: AsyncSession, building_id: UUID) -> list[OccupantNotice]:
    """Get published notices that have not expired."""
    now = datetime.now(UTC)
    query = (
        select(OccupantNotice)
        .where(
            OccupantNotice.building_id == building_id,
            OccupantNotice.status == "published",
        )
        .order_by(OccupantNotice.created_at.desc())
    )
    result = await db.execute(query)
    notices = list(result.scalars().all())
    # Filter out expired notices in Python (expires_at may be None = never expires)
    return [n for n in notices if n.expires_at is None or n.expires_at > now]


async def _get_notice_or_raise(db: AsyncSession, notice_id: UUID) -> OccupantNotice:
    """Get a notice or raise ValueError."""
    result = await db.execute(select(OccupantNotice).where(OccupantNotice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise ValueError("Occupant notice not found")
    return notice
