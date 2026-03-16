"""Sample Optimization API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.sample_optimization import (
    PortfolioSamplingStatus,
    SamplingAdequacyResult,
    SamplingCostEstimate,
    SamplingOptimizationResult,
)
from app.services import sample_optimization_service

router = APIRouter()


@router.get(
    "/buildings/{building_id}/sampling-optimization",
    response_model=SamplingOptimizationResult,
)
async def get_sampling_optimization(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Recommend optimal sample locations for a building."""
    result = await sample_optimization_service.optimize_sampling_plan(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/sampling-cost",
    response_model=SamplingCostEstimate,
)
async def get_sampling_cost(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate sampling cost for a building."""
    result = await sample_optimization_service.estimate_sampling_cost(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/sampling-adequacy",
    response_model=SamplingAdequacyResult,
)
async def get_sampling_adequacy(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate whether current sampling is sufficient."""
    result = await sample_optimization_service.evaluate_sampling_adequacy(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/sampling-status",
    response_model=PortfolioSamplingStatus,
)
async def get_org_sampling_status(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level sampling status for an organization."""
    result = await sample_optimization_service.get_portfolio_sampling_status(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
