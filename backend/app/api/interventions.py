from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.intervention import Intervention
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.intervention import InterventionCreate, InterventionRead, InterventionUpdate
from app.schemas.simulation import SimulationRequest, SimulationResult

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_intervention_or_404(db: AsyncSession, building_id: UUID, intervention_id: UUID) -> Intervention:
    result = await db.execute(
        select(Intervention).where(
            Intervention.id == intervention_id,
            Intervention.building_id == building_id,
        )
    )
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return intervention


@router.get(
    "/buildings/{building_id}/interventions",
    response_model=PaginatedResponse[InterventionRead],
)
async def list_interventions_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    intervention_type: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("interventions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List interventions for a building with optional filters and pagination."""
    await _get_building_or_404(db, building_id)

    query = select(Intervention).where(Intervention.building_id == building_id)
    count_query = select(func.count()).select_from(Intervention).where(Intervention.building_id == building_id)

    if intervention_type:
        query = query.where(Intervention.intervention_type == intervention_type)
        count_query = count_query.where(Intervention.intervention_type == intervention_type)
    if status:
        query = query.where(Intervention.status == status)
        count_query = count_query.where(Intervention.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * size).limit(size)
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
    "/buildings/{building_id}/interventions",
    response_model=InterventionRead,
    status_code=201,
)
async def create_intervention_endpoint(
    building_id: UUID,
    data: InterventionCreate,
    current_user: User = Depends(require_permission("interventions", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new intervention for a building."""
    await _get_building_or_404(db, building_id)

    intervention = Intervention(
        building_id=building_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(intervention)
    await db.commit()
    await db.refresh(intervention)
    return intervention


@router.post(
    "/buildings/{building_id}/interventions/simulate",
    response_model=SimulationResult,
)
async def simulate_interventions_endpoint(
    building_id: UUID,
    data: SimulationRequest,
    current_user: User = Depends(require_permission("interventions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate the impact of planned interventions on building state."""
    from app.services.intervention_simulator import simulate_interventions

    await _get_building_or_404(db, building_id)
    try:
        result = await simulate_interventions(db, building_id, data.interventions)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.get(
    "/buildings/{building_id}/interventions/{intervention_id}",
    response_model=InterventionRead,
)
async def get_intervention_endpoint(
    building_id: UUID,
    intervention_id: UUID,
    current_user: User = Depends(require_permission("interventions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single intervention."""
    await _get_building_or_404(db, building_id)
    return await _get_intervention_or_404(db, building_id, intervention_id)


@router.put(
    "/buildings/{building_id}/interventions/{intervention_id}",
    response_model=InterventionRead,
)
async def update_intervention_endpoint(
    building_id: UUID,
    intervention_id: UUID,
    data: InterventionUpdate,
    current_user: User = Depends(require_permission("interventions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing intervention."""
    await _get_building_or_404(db, building_id)
    intervention = await _get_intervention_or_404(db, building_id, intervention_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(intervention, key, value)

    await db.commit()
    await db.refresh(intervention)
    return intervention


@router.delete(
    "/buildings/{building_id}/interventions/{intervention_id}",
    status_code=204,
)
async def delete_intervention_endpoint(
    building_id: UUID,
    intervention_id: UUID,
    current_user: User = Depends(require_permission("interventions", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete an intervention."""
    await _get_building_or_404(db, building_id)
    intervention = await _get_intervention_or_404(db, building_id, intervention_id)
    await db.delete(intervention)
    await db.commit()
