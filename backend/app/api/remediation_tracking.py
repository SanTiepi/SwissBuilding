"""Remediation Tracking API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.remediation_tracking import (
    BuildingCostTracker,
    BuildingRemediationStatus,
    BuildingRemediationTimeline,
    PortfolioRemediationDashboard,
)
from app.services.remediation_tracking_service import (
    estimate_remediation_timeline,
    get_portfolio_remediation_dashboard,
    get_remediation_cost_tracker,
    get_remediation_status,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/remediation-status",
    response_model=BuildingRemediationStatus,
)
async def get_building_remediation_status(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get per-pollutant remediation progress for a building."""
    try:
        return await get_remediation_status(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/remediation-timeline",
    response_model=BuildingRemediationTimeline,
)
async def get_building_remediation_timeline(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate remediation timeline per pollutant."""
    try:
        return await estimate_remediation_timeline(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/remediation-cost-tracking",
    response_model=BuildingCostTracker,
)
async def get_building_remediation_costs(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Track remediation costs per pollutant."""
    try:
        return await get_remediation_cost_tracker(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{organization_id}/remediation-dashboard",
    response_model=PortfolioRemediationDashboard,
)
async def get_org_remediation_dashboard(
    organization_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get organization-wide remediation dashboard."""
    return await get_portfolio_remediation_dashboard(organization_id, db)
