"""BatiConnect — Contract operations service."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.contract import Contract
from app.models.organization import Organization
from app.models.user import User


async def list_contracts(
    db: AsyncSession,
    building_id: UUID,
    *,
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    contract_type: str | None = None,
) -> tuple[list[Contract], int]:
    query = select(Contract).where(Contract.building_id == building_id)
    count_query = select(func.count()).select_from(Contract).where(Contract.building_id == building_id)

    if status:
        query = query.where(Contract.status == status)
        count_query = count_query.where(Contract.status == status)
    if contract_type:
        query = query.where(Contract.contract_type == contract_type)
        count_query = count_query.where(Contract.contract_type == contract_type)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Contract.date_start.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def get_contract(db: AsyncSession, contract_id: UUID) -> Contract | None:
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    return result.scalar_one_or_none()


async def create_contract(db: AsyncSession, building_id: UUID, data: dict, created_by: UUID | None = None) -> Contract:
    contract = Contract(building_id=building_id, created_by=created_by, **data)
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return contract


async def update_contract(db: AsyncSession, contract: Contract, data: dict) -> Contract:
    for key, value in data.items():
        setattr(contract, key, value)
    await db.flush()
    await db.refresh(contract)
    return contract


async def get_contract_summary(db: AsyncSession, building_id: UUID) -> dict:
    """Compute ContractOpsSummary for a building."""
    all_contracts = (await db.execute(select(Contract).where(Contract.building_id == building_id))).scalars().all()

    active = [c for c in all_contracts if c.status == "active"]

    now = date.today()
    threshold = now + timedelta(days=90)
    expiring_90d = [c for c in active if c.date_end is not None and c.date_end <= threshold]

    annual_cost = sum(c.annual_cost_chf or 0 for c in active)
    auto_renewal_count = sum(1 for c in active if c.auto_renewal)

    return {
        "building_id": str(building_id),
        "total_contracts": len(all_contracts),
        "active_contracts": len(active),
        "annual_cost_chf": annual_cost,
        "expiring_90d": len(expiring_90d),
        "auto_renewal_count": auto_renewal_count,
    }


async def _resolve_counterparty_name(db: AsyncSession, counterparty_type: str, counterparty_id: UUID) -> str | None:
    """Lookup counterparty display name from Contact, User, or Organization."""
    if counterparty_type == "contact":
        result = await db.execute(select(Contact.name).where(Contact.id == counterparty_id))
        return result.scalar_one_or_none()
    elif counterparty_type == "user":
        result = await db.execute(select(User.first_name, User.last_name).where(User.id == counterparty_id))
        row = result.one_or_none()
        return f"{row[0]} {row[1]}" if row else None
    elif counterparty_type == "organization":
        result = await db.execute(select(Organization.name).where(Organization.id == counterparty_id))
        return result.scalar_one_or_none()
    return None


async def enrich_contract(db: AsyncSession, contract: Contract) -> dict:
    """Convert a Contract ORM instance to a dict with display fields populated."""
    data = {c.key: getattr(contract, c.key) for c in contract.__table__.columns}
    data["counterparty_display_name"] = await _resolve_counterparty_name(
        db, contract.counterparty_type, contract.counterparty_id
    )
    return data


async def enrich_contracts(db: AsyncSession, contracts: list[Contract]) -> list[dict]:
    """Enrich a list of contracts with display fields."""
    return [await enrich_contract(db, contract) for contract in contracts]
