"""Cost-benefit analysis API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cost_benefit_analysis import (
    InactionCost,
    InterventionROIResponse,
    PortfolioInvestmentPlan,
    RemediationStrategiesResponse,
)
from app.services.cost_benefit_analysis_service import (
    analyze_intervention_roi,
    calculate_inaction_cost,
    compare_remediation_strategies,
    get_portfolio_investment_plan,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/intervention-roi",
    response_model=InterventionROIResponse,
)
async def get_intervention_roi(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze per-intervention ROI for a building's pollutant remediation."""
    try:
        return await analyze_intervention_roi(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/remediation-strategies",
    response_model=RemediationStrategiesResponse,
)
async def get_remediation_strategies(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare minimal, standard, and comprehensive remediation strategies."""
    try:
        return await compare_remediation_strategies(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/inaction-cost",
    response_model=InactionCost,
)
async def get_inaction_cost(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Calculate the cost of doing nothing about pollutant findings."""
    try:
        return await calculate_inaction_cost(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/investment-plan",
    response_model=PortfolioInvestmentPlan,
)
async def get_investment_plan(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get optimal investment allocation plan across organization buildings."""
    try:
        return await get_portfolio_investment_plan(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
