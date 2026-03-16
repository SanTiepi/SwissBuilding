"""Monitoring Plan API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.monitoring_plan import (
    MonitoringCompliance,
    MonitoringPlan,
    MonitoringSchedule,
    PortfolioMonitoringStatus,
)
from app.services.monitoring_plan_service import (
    evaluate_monitoring_compliance,
    generate_monitoring_plan,
    get_monitoring_schedule,
    get_portfolio_monitoring_status,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/monitoring-plan",
    response_model=MonitoringPlan,
)
async def get_building_monitoring_plan(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate monitoring plan for a building based on its pollutant state."""
    return await generate_monitoring_plan(db, building_id)


@router.get(
    "/buildings/{building_id}/monitoring-schedule",
    response_model=MonitoringSchedule,
)
async def get_building_monitoring_schedule(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return next 12 months of monitoring checks, overdue checks, and cost forecast."""
    return await get_monitoring_schedule(db, building_id)


@router.get(
    "/buildings/{building_id}/monitoring-compliance",
    response_model=MonitoringCompliance,
)
async def get_building_monitoring_compliance(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate whether monitoring obligations are being met."""
    return await evaluate_monitoring_compliance(db, building_id)


@router.get(
    "/organizations/{org_id}/monitoring-status",
    response_model=PortfolioMonitoringStatus,
)
async def get_org_monitoring_status(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return org-level monitoring status across all buildings."""
    return await get_portfolio_monitoring_status(db, org_id)
