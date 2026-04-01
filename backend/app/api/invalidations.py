"""API routes for the invalidation engine."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.invalidation import (
    InvalidationEventRead,
    InvalidationPendingResponse,
    InvalidationResolveRequest,
)
from app.services.invalidation_engine import InvalidationEngine

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/invalidations",
    response_model=list[InvalidationEventRead],
    tags=["Invalidations"],
)
async def get_building_invalidations(
    building_id: UUID,
    status: str | None = Query("detected", description="Filter by status"),
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get invalidation events for a building."""
    await _get_building_or_404(db, building_id)
    engine = InvalidationEngine()
    items, _total = await engine.get_pending_invalidations(
        db,
        building_id=building_id,
        status=status,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return items


@router.get(
    "/invalidations/pending",
    response_model=InvalidationPendingResponse,
    tags=["Invalidations"],
)
async def get_pending_invalidations(
    status: str | None = Query("detected", description="Filter by status"),
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all pending invalidation events across the organization."""
    engine = InvalidationEngine()
    items, total = await engine.get_pending_invalidations(
        db,
        org_id=current_user.organization_id,
        status=status,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total}


@router.post(
    "/invalidations/{event_id}/acknowledge",
    response_model=InvalidationEventRead,
    tags=["Invalidations"],
)
async def acknowledge_invalidation(
    event_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an invalidation event."""
    engine = InvalidationEngine()
    event = await engine.acknowledge_invalidation(db, event_id, current_user.id)
    if event is None:
        raise HTTPException(status_code=404, detail="Invalidation event not found")
    await db.commit()
    return event


@router.post(
    "/invalidations/{event_id}/resolve",
    response_model=InvalidationEventRead,
    tags=["Invalidations"],
)
async def resolve_invalidation(
    event_id: UUID,
    data: InvalidationResolveRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an invalidation event."""
    engine = InvalidationEngine()
    event = await engine.resolve_invalidation(db, event_id, current_user.id, data.resolution_note)
    if event is None:
        raise HTTPException(status_code=404, detail="Invalidation event not found")
    await db.commit()
    return event


@router.post(
    "/invalidations/{event_id}/execute-reaction",
    tags=["Invalidations"],
)
async def execute_reaction(
    event_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Execute the required reaction for an invalidation event."""
    engine = InvalidationEngine()
    result = await engine.execute_reaction(db, event_id)
    if "error" in result and result.get("error") == "Event not found":
        raise HTTPException(status_code=404, detail="Invalidation event not found")
    await db.commit()
    return result
