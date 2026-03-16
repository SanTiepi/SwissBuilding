"""Saved simulation management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.saved_simulation import SavedSimulation
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.saved_simulation import (
    SavedSimulationCreate,
    SavedSimulationRead,
    SavedSimulationUpdate,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_simulation_or_404(db: AsyncSession, building_id: UUID, simulation_id: UUID) -> SavedSimulation:
    result = await db.execute(
        select(SavedSimulation).where(
            SavedSimulation.id == simulation_id,
            SavedSimulation.building_id == building_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(status_code=404, detail="Saved simulation not found")
    return simulation


@router.get(
    "/buildings/{building_id}/simulations",
    response_model=PaginatedResponse[SavedSimulationRead],
)
async def list_simulations_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    simulation_type: str | None = None,
    current_user: User = Depends(require_permission("simulations", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List saved simulations for a building."""
    await _get_building_or_404(db, building_id)

    query = select(SavedSimulation).where(SavedSimulation.building_id == building_id)
    count_query = select(func.count()).select_from(SavedSimulation).where(SavedSimulation.building_id == building_id)

    if simulation_type:
        query = query.where(SavedSimulation.simulation_type == simulation_type)
        count_query = count_query.where(SavedSimulation.simulation_type == simulation_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(SavedSimulation.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post(
    "/buildings/{building_id}/simulations",
    response_model=SavedSimulationRead,
    status_code=201,
)
async def create_simulation_endpoint(
    building_id: UUID,
    data: SavedSimulationCreate,
    current_user: User = Depends(require_permission("simulations", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Save a simulation result."""
    await _get_building_or_404(db, building_id)

    simulation = SavedSimulation(
        building_id=building_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(simulation)
    await db.commit()
    await db.refresh(simulation)
    return simulation


@router.get(
    "/buildings/{building_id}/simulations/{simulation_id}",
    response_model=SavedSimulationRead,
)
async def get_simulation_endpoint(
    building_id: UUID,
    simulation_id: UUID,
    current_user: User = Depends(require_permission("simulations", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single saved simulation."""
    await _get_building_or_404(db, building_id)
    return await _get_simulation_or_404(db, building_id, simulation_id)


@router.put(
    "/buildings/{building_id}/simulations/{simulation_id}",
    response_model=SavedSimulationRead,
)
async def update_simulation_endpoint(
    building_id: UUID,
    simulation_id: UUID,
    data: SavedSimulationUpdate,
    current_user: User = Depends(require_permission("simulations", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a saved simulation."""
    await _get_building_or_404(db, building_id)
    simulation = await _get_simulation_or_404(db, building_id, simulation_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(simulation, key, value)

    await db.commit()
    await db.refresh(simulation)
    return simulation


@router.delete(
    "/buildings/{building_id}/simulations/{simulation_id}",
    status_code=204,
)
async def delete_simulation_endpoint(
    building_id: UUID,
    simulation_id: UUID,
    current_user: User = Depends(require_permission("simulations", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved simulation."""
    await _get_building_or_404(db, building_id)
    simulation = await _get_simulation_or_404(db, building_id, simulation_id)
    await db.delete(simulation)
    await db.commit()
