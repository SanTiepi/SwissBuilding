"""Field observations API — capture site visit findings and evidence from the field."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.field_observation import (
    FieldObservationCreate,
    FieldObservationRead,
    FieldObservationSummary,
    FieldObservationUpdate,
    FieldObservationVerify,
)
from app.services.field_observation_service import (
    create_observation,
    get_observation,
    get_observation_summary,
    list_observations,
    update_observation,
    verify_observation,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


def _enrich_observation(obs, observer_name: str | None = None) -> dict:
    """Convert observation to dict with observer_name."""
    data = {c.key: getattr(obs, c.key) for c in obs.__table__.columns}
    data["observer_name"] = observer_name
    return data


@router.post(
    "/buildings/{building_id}/field-observations",
    response_model=FieldObservationRead,
    status_code=201,
)
async def create_observation_endpoint(
    building_id: UUID,
    data: FieldObservationCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new field observation for a building."""
    await _get_building_or_404(db, building_id)
    obs = await create_observation(db, building_id, current_user.id, data)
    return _enrich_observation(obs, f"{current_user.first_name} {current_user.last_name}")


@router.get(
    "/buildings/{building_id}/field-observations",
    response_model=PaginatedResponse[FieldObservationRead],
)
async def list_observations_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    observation_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    zone_id: UUID | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List field observations for a building with filters and pagination."""
    await _get_building_or_404(db, building_id)
    items, total = await list_observations(
        db,
        building_id,
        observation_type=observation_type,
        severity=severity,
        status=status,
        zone_id=zone_id,
        page=page,
        size=size,
    )
    pages = (total + size - 1) // size if total > 0 else 0

    enriched = []
    for obs in items:
        # Lazy-load observer name
        observer = await db.get(User, obs.observer_id)
        name = f"{observer.first_name} {observer.last_name}" if observer else None
        enriched.append(_enrich_observation(obs, name))

    return {"items": enriched, "total": total, "page": page, "size": size, "pages": pages}


@router.get(
    "/buildings/{building_id}/field-observations/summary",
    response_model=FieldObservationSummary,
)
async def observation_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated summary of field observations for a building."""
    await _get_building_or_404(db, building_id)
    return await get_observation_summary(db, building_id)


@router.get(
    "/field-observations/{observation_id}",
    response_model=FieldObservationRead,
)
async def get_observation_endpoint(
    observation_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single field observation by ID."""
    obs = await get_observation(db, observation_id)
    if obs is None:
        raise HTTPException(status_code=404, detail="Field observation not found")
    observer = await db.get(User, obs.observer_id)
    name = f"{observer.first_name} {observer.last_name}" if observer else None
    return _enrich_observation(obs, name)


@router.put(
    "/field-observations/{observation_id}",
    response_model=FieldObservationRead,
)
async def update_observation_endpoint(
    observation_id: UUID,
    data: FieldObservationUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a field observation."""
    obs = await update_observation(db, observation_id, data)
    if obs is None:
        raise HTTPException(status_code=404, detail="Field observation not found")
    observer = await db.get(User, obs.observer_id)
    name = f"{observer.first_name} {observer.last_name}" if observer else None
    return _enrich_observation(obs, name)


@router.post(
    "/field-observations/{observation_id}/verify",
    response_model=FieldObservationRead,
)
async def verify_observation_endpoint(
    observation_id: UUID,
    data: FieldObservationVerify,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Verify or unverify a field observation."""
    obs = await verify_observation(db, observation_id, current_user.id, data)
    if obs is None:
        raise HTTPException(status_code=404, detail="Field observation not found")
    observer = await db.get(User, obs.observer_id)
    name = f"{observer.first_name} {observer.last_name}" if observer else None
    return _enrich_observation(obs, name)
