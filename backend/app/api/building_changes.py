"""Building Change Grammar API routes — observations, events, deltas, signals."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_change import (
    BuildingDeltaCompute,
    BuildingDeltaRead,
    BuildingEventCreate,
    BuildingEventRead,
    BuildingObservationCreate,
    BuildingObservationRead,
    BuildingSignalRead,
    ChangeTimelineEntry,
    SignalResolveRequest,
)
from app.services import change_tracker_service

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/observations",
    response_model=BuildingObservationRead,
    status_code=201,
    tags=["Building Changes"],
)
async def record_observation(
    building_id: UUID,
    data: BuildingObservationCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a point-in-time observation about a building."""
    await _get_building_or_404(db, building_id)
    obs = await change_tracker_service.record_observation(
        db,
        building_id,
        current_user.id,
        observation_type=data.observation_type,
        observer_role=data.observer_role,
        target_type=data.target_type,
        subject=data.subject,
        value=data.value,
        observed_at=data.observed_at,
        case_id=data.case_id,
        target_id=data.target_id,
        unit=data.unit,
        confidence=data.confidence,
        method=data.method,
        source_document_id=data.source_document_id,
        source_extraction_id=data.source_extraction_id,
        notes=data.notes,
    )
    await db.commit()
    await db.refresh(obs)
    return obs


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/events",
    response_model=BuildingEventRead,
    status_code=201,
    tags=["Building Changes"],
)
async def record_event(
    building_id: UUID,
    data: BuildingEventCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a significant building event."""
    await _get_building_or_404(db, building_id)
    evt = await change_tracker_service.record_event(
        db,
        building_id,
        data.event_type,
        data.title,
        actor_id=current_user.id,
        occurred_at=data.occurred_at,
        description=data.description,
        case_id=data.case_id,
        impact_scope=data.impact_scope,
        impact_target_id=data.impact_target_id,
        impact_description=data.impact_description,
        severity=data.severity,
        source_type=data.source_type,
        source_id=data.source_id,
    )
    await db.commit()
    await db.refresh(evt)
    return evt


# ---------------------------------------------------------------------------
# Deltas
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/deltas/compute",
    response_model=BuildingDeltaRead,
    status_code=201,
    tags=["Building Changes"],
)
async def compute_delta(
    building_id: UUID,
    data: BuildingDeltaCompute,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compute a delta between two points in time."""
    await _get_building_or_404(db, building_id)
    delta = await change_tracker_service.compute_delta(
        db,
        building_id,
        data.delta_type,
        data.period_start,
        data.period_end,
    )
    await db.commit()
    await db.refresh(delta)
    return delta


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/signals/detect",
    response_model=list[BuildingSignalRead],
    tags=["Building Changes"],
)
async def detect_signals(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect signals from recent observations, events, and deltas."""
    await _get_building_or_404(db, building_id)
    signals = await change_tracker_service.detect_signals(db, building_id)
    await db.commit()
    return signals


@router.get(
    "/buildings/{building_id}/signals",
    response_model=list[BuildingSignalRead],
    tags=["Building Changes"],
)
async def list_active_signals(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List active signals for a building."""
    await _get_building_or_404(db, building_id)
    return await change_tracker_service.get_active_signals(db, building_id)


@router.get(
    "/portfolio/signals",
    response_model=list[BuildingSignalRead],
    tags=["Building Changes"],
)
async def list_portfolio_signals(
    severity: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List recent signals across all buildings (portfolio-level)."""
    return await change_tracker_service.get_portfolio_signals(db, severity=severity, status=status, limit=limit)


# ---------------------------------------------------------------------------
# Unified change timeline
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/changes",
    response_model=list[ChangeTimelineEntry],
    tags=["Building Changes"],
)
async def get_change_timeline(
    building_id: UUID,
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get unified change timeline: observations + events + deltas + signals."""
    await _get_building_or_404(db, building_id)
    return await change_tracker_service.get_change_timeline(
        db, building_id, since=since, until=until, limit=limit, offset=offset
    )


# ---------------------------------------------------------------------------
# Signal lifecycle
# ---------------------------------------------------------------------------


@router.post(
    "/signals/{signal_id}/acknowledge",
    response_model=BuildingSignalRead,
    tags=["Building Changes"],
)
async def acknowledge_signal(
    signal_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a signal without resolving it."""
    signal = await change_tracker_service.acknowledge_signal(db, signal_id, current_user.id)
    await db.commit()
    await db.refresh(signal)
    return signal


@router.post(
    "/signals/{signal_id}/resolve",
    response_model=BuildingSignalRead,
    tags=["Building Changes"],
)
async def resolve_signal(
    signal_id: UUID,
    data: SignalResolveRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a signal."""
    signal = await change_tracker_service.resolve_signal(db, signal_id, current_user.id, data.resolution_note)
    await db.commit()
    await db.refresh(signal)
    return signal
