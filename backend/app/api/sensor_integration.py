"""Sensor Integration API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.sensor_integration import (
    BuildingSensorAlerts,
    BuildingSensorOverview,
    BuildingSensorTrends,
    PortfolioSensorStatus,
)
from app.services.sensor_integration_service import (
    get_building_sensor_alerts,
    get_building_sensor_overview,
    get_building_sensor_trends,
    get_portfolio_sensor_status,
)

router = APIRouter()


@router.get(
    "/sensor-integration/buildings/{building_id}/overview",
    response_model=BuildingSensorOverview,
)
async def sensor_overview(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get sensor overview for a building including devices and latest readings."""
    return await get_building_sensor_overview(building_id, db)


@router.get(
    "/sensor-integration/buildings/{building_id}/alerts",
    response_model=BuildingSensorAlerts,
)
async def sensor_alerts(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get sensor alerts for a building based on threshold exceedances."""
    return await get_building_sensor_alerts(building_id, db)


@router.get(
    "/sensor-integration/buildings/{building_id}/trends",
    response_model=BuildingSensorTrends,
)
async def sensor_trends(
    building_id: uuid.UUID,
    period_days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get sensor trend data for a building over a specified period."""
    return await get_building_sensor_trends(building_id, db, period_days=period_days)


@router.get(
    "/sensor-integration/organizations/{org_id}/status",
    response_model=PortfolioSensorStatus,
)
async def portfolio_sensor_status(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated sensor status across all buildings in an organization."""
    return await get_portfolio_sensor_status(org_id, db)
