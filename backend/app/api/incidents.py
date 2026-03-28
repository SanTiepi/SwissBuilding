"""BatiConnect - Incident & Damage Memory API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.incident import (
    DamageObservationCreate,
    DamageObservationRead,
    IncidentEpisodeCreate,
    IncidentEpisodeListRead,
    IncidentEpisodeRead,
    IncidentEpisodeUpdate,
    IncidentResolveRequest,
    IncidentRiskProfile,
    InsurerIncidentSummary,
)
from app.services.incident_service import (
    add_damage_observation,
    create_incident,
    get_building_incidents,
    get_incident,
    get_incident_risk_profile,
    get_insurer_incident_summary,
    get_recurring_incidents,
    resolve_incident,
    update_incident,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_incident_or_404(db: AsyncSession, incident_id: UUID):
    incident = await get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


# ---------------------------------------------------------------------------
# Incident CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/incidents",
    response_model=IncidentEpisodeRead,
    status_code=201,
    tags=["Incidents"],
)
async def create_incident_endpoint(
    building_id: UUID,
    payload: IncidentEpisodeCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a new incident for a building."""
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    incident = await create_incident(
        db,
        building_id,
        current_user.organization_id,
        incident_type=data.pop("incident_type"),
        title=data.pop("title"),
        severity=data.pop("severity", "minor"),
        discovered_at=data.pop("discovered_at", None),
        created_by=current_user.id,
        **data,
    )
    await db.commit()
    await db.refresh(incident)
    return incident


@router.get(
    "/buildings/{building_id}/incidents",
    response_model=PaginatedResponse[IncidentEpisodeListRead],
    tags=["Incidents"],
)
async def list_incidents_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    incident_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List incidents for a building."""
    await _get_building_or_404(db, building_id)
    items, total = await get_building_incidents(
        db, building_id, status=status, incident_type=incident_type, page=page, size=size
    )
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.put(
    "/incidents/{incident_id}",
    response_model=IncidentEpisodeRead,
    tags=["Incidents"],
)
async def update_incident_endpoint(
    incident_id: UUID,
    payload: IncidentEpisodeUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an incident."""
    await _get_incident_or_404(db, incident_id)
    data = payload.model_dump(exclude_unset=True)
    incident = await update_incident(db, incident_id, **data)
    await db.commit()
    await db.refresh(incident)
    return incident


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=IncidentEpisodeRead,
    tags=["Incidents"],
)
async def resolve_incident_endpoint(
    incident_id: UUID,
    payload: IncidentResolveRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Mark an incident as resolved."""
    await _get_incident_or_404(db, incident_id)
    incident = await resolve_incident(
        db,
        incident_id,
        resolution_description=payload.resolution_description,
        repair_cost_chf=payload.repair_cost_chf,
    )
    await db.commit()
    await db.refresh(incident)
    return incident


@router.get(
    "/buildings/{building_id}/incidents/recurring",
    response_model=list[IncidentEpisodeListRead],
    tags=["Incidents"],
)
async def recurring_incidents_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get recurring incidents for a building."""
    await _get_building_or_404(db, building_id)
    return await get_recurring_incidents(db, building_id)


# ---------------------------------------------------------------------------
# Damage Observations
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/damage-observations",
    response_model=DamageObservationRead,
    status_code=201,
    tags=["Incidents"],
)
async def create_damage_observation_endpoint(
    building_id: UUID,
    payload: DamageObservationCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a damage observation for a building."""
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    obs = await add_damage_observation(
        db,
        building_id,
        observed_by_id=current_user.id,
        **data,
    )
    await db.commit()
    await db.refresh(obs)
    return obs


# ---------------------------------------------------------------------------
# Risk Profile & Insurer Summary
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/incident-risk-profile",
    response_model=IncidentRiskProfile,
    tags=["Incidents"],
)
async def incident_risk_profile_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Risk profile based on incident history."""
    await _get_building_or_404(db, building_id)
    return await get_incident_risk_profile(db, building_id)


@router.get(
    "/buildings/{building_id}/insurer-incident-summary",
    response_model=InsurerIncidentSummary,
    tags=["Incidents"],
)
async def insurer_incident_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Summary formatted for insurer readiness (safe_to_insure)."""
    await _get_building_or_404(db, building_id)
    return await get_insurer_incident_summary(db, building_id)
