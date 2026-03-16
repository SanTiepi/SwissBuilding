"""Building Health Index API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_health_index import (
    HealthBreakdown,
    HealthIndex,
    HealthTrajectory,
    PortfolioHealthDashboard,
)
from app.services.building_health_index_service import (
    calculate_health_index,
    get_health_breakdown,
    get_portfolio_health_dashboard,
    predict_health_trajectory,
)

router = APIRouter()


@router.get("/buildings/{building_id}/health-index", response_model=HealthIndex)
async def get_building_health_index(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get composite health index for a building."""
    try:
        return await calculate_health_index(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/health-breakdown", response_model=HealthBreakdown)
async def get_building_health_breakdown(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed health breakdown with improvement levers."""
    try:
        return await get_health_breakdown(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/health-trajectory", response_model=HealthTrajectory)
async def get_building_health_trajectory(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get 12-month health trajectory projection."""
    try:
        return await predict_health_trajectory(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/health-dashboard",
    response_model=PortfolioHealthDashboard,
)
async def get_org_health_dashboard(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level health dashboard for an organization."""
    return await get_portfolio_health_dashboard(db, org_id)
