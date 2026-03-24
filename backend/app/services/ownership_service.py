"""BatiConnect — Ownership operations service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.organization import Organization
from app.models.ownership_record import OwnershipRecord
from app.models.user import User


async def list_ownership_records(
    db: AsyncSession,
    building_id: UUID,
    *,
    page: int = 1,
    size: int = 20,
    status: str | None = None,
) -> tuple[list[OwnershipRecord], int]:
    query = select(OwnershipRecord).where(OwnershipRecord.building_id == building_id)
    count_query = select(func.count()).select_from(OwnershipRecord).where(OwnershipRecord.building_id == building_id)

    if status:
        query = query.where(OwnershipRecord.status == status)
        count_query = count_query.where(OwnershipRecord.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(OwnershipRecord.acquisition_date.desc().nullslast()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def get_ownership_record(db: AsyncSession, record_id: UUID) -> OwnershipRecord | None:
    result = await db.execute(select(OwnershipRecord).where(OwnershipRecord.id == record_id))
    return result.scalar_one_or_none()


async def create_ownership_record(
    db: AsyncSession, building_id: UUID, data: dict, created_by: UUID | None = None
) -> OwnershipRecord:
    record = OwnershipRecord(building_id=building_id, created_by=created_by, **data)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def update_ownership_record(db: AsyncSession, record: OwnershipRecord, data: dict) -> OwnershipRecord:
    for key, value in data.items():
        setattr(record, key, value)
    await db.flush()
    await db.refresh(record)
    return record


async def get_ownership_summary(db: AsyncSession, building_id: UUID) -> dict:
    """Compute OwnershipOpsSummary for a building."""
    all_records = (
        (await db.execute(select(OwnershipRecord).where(OwnershipRecord.building_id == building_id))).scalars().all()
    )

    active = [r for r in all_records if r.status == "active"]

    total_share_pct = sum(r.share_pct or 0 for r in active)

    # Count distinct owners (by owner_id)
    owner_ids = {r.owner_id for r in active}
    owner_count = len(owner_ids)
    co_ownership = owner_count > 1

    return {
        "building_id": str(building_id),
        "total_records": len(all_records),
        "active_records": len(active),
        "total_share_pct": total_share_pct,
        "owner_count": owner_count,
        "co_ownership": co_ownership,
    }


async def _resolve_owner_name(db: AsyncSession, owner_type: str, owner_id: UUID) -> str | None:
    """Lookup owner display name from Contact, User, or Organization."""
    if owner_type == "contact":
        result = await db.execute(select(Contact.name).where(Contact.id == owner_id))
        return result.scalar_one_or_none()
    elif owner_type == "user":
        result = await db.execute(select(User.first_name, User.last_name).where(User.id == owner_id))
        row = result.one_or_none()
        return f"{row[0]} {row[1]}" if row else None
    elif owner_type == "organization":
        result = await db.execute(select(Organization.name).where(Organization.id == owner_id))
        return result.scalar_one_or_none()
    return None


async def enrich_ownership(db: AsyncSession, record: OwnershipRecord) -> dict:
    """Convert an OwnershipRecord ORM instance to a dict with display fields populated."""
    data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
    data["owner_display_name"] = await _resolve_owner_name(db, record.owner_type, record.owner_id)
    return data


async def enrich_ownerships(db: AsyncSession, records: list[OwnershipRecord]) -> list[dict]:
    """Enrich a list of ownership records with display fields."""
    return [await enrich_ownership(db, record) for record in records]
