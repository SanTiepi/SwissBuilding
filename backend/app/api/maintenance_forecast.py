"""Maintenance Forecast API endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.maintenance_forecast import (
    MaintenanceBudget,
    MaintenanceForecast,
    MaintenanceItem,
    PortfolioMaintenanceForecast,
)
from app.services.maintenance_forecast_service import (
    forecast_building_maintenance,
    forecast_portfolio_maintenance,
    get_maintenance_budget,
    get_upcoming_maintenance,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/maintenance-forecast",
    response_model=MaintenanceForecast,
)
async def get_building_maintenance_forecast(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return full maintenance forecast for a building."""
    return await forecast_building_maintenance(db, building_id)


@router.get(
    "/buildings/{building_id}/maintenance-budget",
    response_model=MaintenanceBudget,
)
async def get_building_maintenance_budget(
    building_id: uuid.UUID,
    years: int = Query(5, ge=1, le=10),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return yearly maintenance budget forecast."""
    return await get_maintenance_budget(db, building_id, years=years)


@router.get(
    "/portfolio/maintenance-forecast",
    response_model=PortfolioMaintenanceForecast,
)
async def get_portfolio_maintenance(
    org_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregate maintenance forecast across all buildings."""
    return await forecast_portfolio_maintenance(db, org_id=org_id)


@router.get(
    "/buildings/{building_id}/upcoming-maintenance",
    response_model=list[MaintenanceItem],
)
async def get_building_upcoming_maintenance(
    building_id: uuid.UUID,
    months: int = Query(12, ge=1, le=60),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return maintenance items due within the next N months."""
    return await get_upcoming_maintenance(db, building_id, months=months)
