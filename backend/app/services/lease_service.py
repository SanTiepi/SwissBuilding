"""BatiConnect — Lease operations service."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.lease import Lease
from app.models.organization import Organization
from app.models.unit import Unit
from app.models.user import User
from app.models.zone import Zone


async def list_leases(
    db: AsyncSession,
    building_id: UUID,
    *,
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    lease_type: str | None = None,
) -> tuple[list[Lease], int]:
    query = select(Lease).where(Lease.building_id == building_id)
    count_query = select(func.count()).select_from(Lease).where(Lease.building_id == building_id)

    if status:
        query = query.where(Lease.status == status)
        count_query = count_query.where(Lease.status == status)
    if lease_type:
        query = query.where(Lease.lease_type == lease_type)
        count_query = count_query.where(Lease.lease_type == lease_type)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Lease.date_start.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def get_lease(db: AsyncSession, lease_id: UUID) -> Lease | None:
    result = await db.execute(select(Lease).where(Lease.id == lease_id))
    return result.scalar_one_or_none()


async def create_lease(db: AsyncSession, building_id: UUID, data: dict, created_by: UUID | None = None) -> Lease:
    lease = Lease(building_id=building_id, created_by=created_by, **data)
    db.add(lease)
    await db.flush()
    await db.refresh(lease)
    return lease


async def update_lease(db: AsyncSession, lease: Lease, data: dict) -> Lease:
    for key, value in data.items():
        setattr(lease, key, value)
    await db.flush()
    await db.refresh(lease)
    return lease


async def get_lease_summary(db: AsyncSession, building_id: UUID) -> dict:
    """Compute LeaseOpsSummary for a building."""
    all_leases = (await db.execute(select(Lease).where(Lease.building_id == building_id))).scalars().all()

    active = [ls for ls in all_leases if ls.status == "active"]
    disputed = [ls for ls in all_leases if ls.status == "disputed"]

    now = date.today()
    threshold = now + timedelta(days=90)
    expiring_90d = [ls for ls in active if ls.date_end is not None and ls.date_end <= threshold]

    monthly_rent = sum(ls.rent_monthly_chf or 0 for ls in active)
    monthly_charges = sum(ls.charges_monthly_chf or 0 for ls in active)

    return {
        "building_id": str(building_id),
        "total_leases": len(all_leases),
        "active_leases": len(active),
        "monthly_rent_chf": monthly_rent,
        "monthly_charges_chf": monthly_charges,
        "expiring_90d": len(expiring_90d),
        "disputed_count": len(disputed),
    }


async def _resolve_tenant_name(db: AsyncSession, tenant_type: str, tenant_id: UUID) -> str | None:
    """Lookup tenant display name from Contact, User, or Organization."""
    if tenant_type == "contact":
        result = await db.execute(select(Contact.name).where(Contact.id == tenant_id))
        return result.scalar_one_or_none()
    elif tenant_type == "user":
        result = await db.execute(select(User.first_name, User.last_name).where(User.id == tenant_id))
        row = result.one_or_none()
        return f"{row[0]} {row[1]}" if row else None
    elif tenant_type == "organization":
        result = await db.execute(select(Organization.name).where(Organization.id == tenant_id))
        return result.scalar_one_or_none()
    return None


async def _resolve_unit_label(db: AsyncSession, unit_id: UUID | None) -> str | None:
    """Lookup unit label (prefer name, fallback to reference_code)."""
    if not unit_id:
        return None
    result = await db.execute(select(Unit.reference_code, Unit.name).where(Unit.id == unit_id))
    row = result.one_or_none()
    if row:
        return row[1] or row[0]  # prefer name, fallback to reference_code
    return None


async def _resolve_zone_name(db: AsyncSession, zone_id: UUID | None) -> str | None:
    """Lookup zone name."""
    if not zone_id:
        return None
    result = await db.execute(select(Zone.name).where(Zone.id == zone_id))
    return result.scalar_one_or_none()


async def enrich_lease(db: AsyncSession, lease: Lease) -> dict:
    """Convert a Lease ORM instance to a dict with display fields populated."""
    data = {c.key: getattr(lease, c.key) for c in lease.__table__.columns}
    data["tenant_display_name"] = await _resolve_tenant_name(db, lease.tenant_type, lease.tenant_id)
    data["unit_label"] = await _resolve_unit_label(db, lease.unit_id)
    data["zone_name"] = await _resolve_zone_name(db, lease.zone_id)
    return data


async def enrich_leases(db: AsyncSession, leases: list[Lease]) -> list[dict]:
    """Enrich a list of leases with display fields."""
    return [await enrich_lease(db, lease) for lease in leases]
