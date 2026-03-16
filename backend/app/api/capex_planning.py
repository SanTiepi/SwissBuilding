"""CAPEX planning API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.capex_planning import (
    BuildingCapexPlan,
    BuildingInvestmentForecast,
    PortfolioCapexSummary,
    ReserveFundStatus,
)
from app.services.capex_planning_service import (
    evaluate_reserve_fund,
    forecast_investment_scenarios,
    generate_building_capex_plan,
    get_portfolio_capex_summary,
)

router = APIRouter()


@router.get(
    "/capex-planning/buildings/{building_id}/plan",
    response_model=BuildingCapexPlan,
)
async def get_capex_plan(
    building_id: UUID,
    horizon_years: int = 5,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a CAPEX plan for a building."""
    try:
        return await generate_building_capex_plan(building_id, db, horizon_years)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/capex-planning/buildings/{building_id}/reserve-fund",
    response_model=ReserveFundStatus,
)
async def get_reserve_fund(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate reserve fund adequacy for a building."""
    try:
        return await evaluate_reserve_fund(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/capex-planning/buildings/{building_id}/investment-forecast",
    response_model=BuildingInvestmentForecast,
)
async def get_investment_forecast(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Forecast investment scenarios for a building."""
    try:
        return await forecast_investment_scenarios(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/capex-planning/organizations/{org_id}/summary",
    response_model=PortfolioCapexSummary,
)
async def get_capex_summary(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level CAPEX summary for an organization."""
    try:
        return await get_portfolio_capex_summary(org_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
