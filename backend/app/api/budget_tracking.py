"""Budget tracking API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.budget_tracking import (
    BudgetOverview,
    CostVarianceResponse,
    PortfolioBudgetSummary,
    QuarterlySpendResponse,
)
from app.services.budget_tracking_service import (
    forecast_quarterly_spend,
    get_building_budget_overview,
    get_portfolio_budget_summary,
    track_cost_variance,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/budget-overview",
    response_model=BudgetOverview,
)
async def get_budget_overview(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get budget status for a building: estimated, spent, remaining, burn rate."""
    try:
        return await get_building_budget_overview(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/cost-variance",
    response_model=CostVarianceResponse,
)
async def get_cost_variance(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Track per-intervention cost variance: estimated vs actual."""
    try:
        return await track_cost_variance(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/quarterly-forecast",
    response_model=QuarterlySpendResponse,
)
async def get_quarterly_forecast(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Forecast quarterly spend for next 4 quarters based on planned interventions."""
    try:
        return await forecast_quarterly_spend(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/budget-summary",
    response_model=PortfolioBudgetSummary,
)
async def get_org_budget_summary(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level budget summary for an organization."""
    try:
        return await get_portfolio_budget_summary(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
