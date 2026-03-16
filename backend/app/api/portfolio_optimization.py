"""Portfolio optimization API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.portfolio_optimization import (
    BudgetAllocationRequest,
    BudgetAllocationResult,
    PortfolioActionPlan,
    PortfolioPrioritization,
    RiskDistributionAnalysis,
)
from app.services.portfolio_optimization_service import (
    analyze_portfolio_risk_distribution,
    get_portfolio_action_plan,
    prioritize_buildings,
    simulate_budget_allocation,
)

router = APIRouter()


@router.get("/portfolio/prioritization", response_model=PortfolioPrioritization)
async def portfolio_prioritization(
    org_id: UUID | None = Query(None),
    budget_chf: float | None = Query(None, gt=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get prioritized list of buildings for intervention."""
    return await prioritize_buildings(db, org_id=org_id, budget_chf=budget_chf)


@router.get("/portfolio/action-plan", response_model=PortfolioActionPlan)
async def portfolio_action_plan(
    org_id: UUID | None = Query(None),
    max_buildings: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get action plan for top N priority buildings."""
    return await get_portfolio_action_plan(db, org_id=org_id, max_buildings=max_buildings)


@router.get("/portfolio/risk-distribution", response_model=RiskDistributionAnalysis)
async def portfolio_risk_distribution(
    org_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze risk distribution across portfolio dimensions."""
    return await analyze_portfolio_risk_distribution(db, org_id=org_id)


@router.post("/portfolio/budget-allocation", response_model=BudgetAllocationResult)
async def portfolio_budget_allocation(
    body: BudgetAllocationRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate optimal budget allocation across selected buildings."""
    return await simulate_budget_allocation(db, building_ids=body.building_ids, total_budget_chf=body.total_budget_chf)
