"""Remediation cost estimation API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.remediation_cost import (
    BuildingCostComparison,
    CompareRequest,
    CostFactors,
    PollutantCostBreakdown,
    RemediationCostEstimate,
)
from app.services.remediation_cost_service import (
    compare_building_costs,
    estimate_building_cost,
    estimate_pollutant_cost,
    get_cost_factors,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/remediation-costs",
    response_model=RemediationCostEstimate,
)
async def get_remediation_cost_estimate(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate full remediation costs for a building."""
    try:
        return await estimate_building_cost(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/remediation-costs/{pollutant_type}",
    response_model=PollutantCostBreakdown,
)
async def get_pollutant_cost(
    building_id: UUID,
    pollutant_type: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed cost breakdown for a specific pollutant."""
    try:
        return await estimate_pollutant_cost(db, building_id, pollutant_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/remediation-costs/compare",
    response_model=list[BuildingCostComparison],
)
async def compare_costs(
    body: CompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare remediation costs across multiple buildings (max 10)."""
    try:
        return await compare_building_costs(db, body.building_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/cost-factors",
    response_model=CostFactors,
)
async def get_building_cost_factors(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get factors that drive remediation costs for a building."""
    try:
        return await get_cost_factors(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
