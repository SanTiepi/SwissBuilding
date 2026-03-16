"""Weak signal watchtower API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.weak_signal import (
    PortfolioWatchReport,
    WatchRule,
    WeakSignal,
    WeakSignalReport,
)
from app.services.weak_signal_watchtower import (
    get_buildings_on_critical_path,
    get_signal_history,
    get_watch_rules,
    scan_building_weak_signals,
    scan_portfolio_weak_signals,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/weak-signals",
    response_model=WeakSignalReport,
)
async def get_building_weak_signals(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Scan a building for weak signals and return a report."""
    await _get_building_or_404(db, building_id)
    return await scan_building_weak_signals(db, building_id)


@router.get(
    "/portfolio/weak-signals",
    response_model=PortfolioWatchReport,
)
async def get_portfolio_weak_signals(
    organization_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Scan portfolio buildings for weak signals and return aggregated report."""
    return await scan_portfolio_weak_signals(db, organization_id=organization_id, limit=limit)


@router.get(
    "/portfolio/critical-path",
    response_model=list[dict],
)
async def get_critical_path_buildings(
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return buildings on critical path (3+ weak signals detected)."""
    return await get_buildings_on_critical_path(db, organization_id=organization_id)


@router.get(
    "/buildings/{building_id}/weak-signals/history",
    response_model=list[WeakSignal],
)
async def get_building_weak_signal_history(
    building_id: UUID,
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return historical weak signals from change signal records."""
    await _get_building_or_404(db, building_id)
    return await get_signal_history(db, building_id, days=days)


@router.get(
    "/weak-signals/rules",
    response_model=list[WatchRule],
)
async def list_watch_rules(
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """Return the list of active detection rules."""
    return get_watch_rules()
