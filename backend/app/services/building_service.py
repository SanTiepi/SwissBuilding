"""
SwissBuildingOS - Building Service

CRUD operations for buildings with risk score auto-creation and event tracking.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.event import Event
from app.schemas.building import BuildingCreate, BuildingUpdate
from app.services.risk_engine import calculate_building_risk


async def create_building(
    db: AsyncSession,
    data: BuildingCreate,
    created_by: UUID,
    *,
    organization_id: UUID | None = None,
) -> Building:
    """
    Create a building, auto-compute and attach a BuildingRiskScore,
    and create a 'construction' Event. Returns the committed Building.
    """
    building = Building(
        **data.model_dump(),
        created_by=created_by,
        organization_id=organization_id,
        status="active",
    )
    db.add(building)
    await db.flush()  # get building.id

    # Auto-create risk score using the risk engine
    risk_score = await calculate_building_risk(db, building)
    building.risk_scores = risk_score
    db.add(risk_score)

    # Create construction event
    construction_year = data.construction_year
    try:
        event_date = (
            date(construction_year, 1, 1) if construction_year and 1 <= construction_year <= 9999 else date.today()
        )
    except (ValueError, OverflowError):
        event_date = date.today()
    event = Event(
        building_id=building.id,
        event_type="construction",
        date=event_date,
        title=f"Construction ({construction_year or 'unknown'})",
        description=f"Building constructed: {data.address}, {data.city}",
        created_by=created_by,
    )
    db.add(event)

    await db.commit()
    return building


async def get_building(db: AsyncSession, building_id: UUID) -> Building | None:
    """Get a single building by ID with eager-loaded risk_scores."""
    stmt = select(Building).options(selectinload(Building.risk_scores)).where(Building.id == building_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_buildings(
    db: AsyncSession,
    page: int,
    size: int,
    canton: str | None = None,
    city: str | None = None,
    postal_code: str | None = None,
    building_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    search: str | None = None,
) -> tuple[list[Building], int]:
    """
    List buildings with filters and pagination.
    Returns (buildings_list, total_count).
    """
    base = select(Building).where(Building.status != "archived")

    if canton:
        base = base.where(Building.canton == canton.upper())
    if city:
        base = base.where(Building.city.ilike(f"%{city}%"))
    if postal_code:
        base = base.where(Building.postal_code == postal_code)
    if building_type:
        base = base.where(Building.building_type == building_type)
    if year_from is not None:
        base = base.where(Building.construction_year >= year_from)
    if year_to is not None:
        base = base.where(Building.construction_year <= year_to)
    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                Building.address.ilike(pattern),
                Building.city.ilike(pattern),
                Building.egrid.ilike(pattern),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * size
    data_stmt = base.order_by(Building.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(data_stmt)
    buildings = list(result.scalars().all())

    return buildings, total


async def update_building(db: AsyncSession, building_id: UUID, data: BuildingUpdate) -> Building | None:
    """
    Partially update a building. Only fields with non-None values are applied.
    Returns the updated Building or None if not found.
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()

    if building is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(building, field, value)

    await db.commit()

    # Re-fetch with eager-loaded risk_scores
    stmt = select(Building).options(selectinload(Building.risk_scores)).where(Building.id == building_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_building(db: AsyncSession, building_id: UUID) -> bool:
    """
    Soft-delete a building by setting status to 'archived'.
    Returns True if the building was found and archived, False otherwise.
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()

    if building is None:
        return False

    building.status = "archived"
    await db.commit()
    return True
