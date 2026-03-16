"""Energy performance API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.energy_performance import (
    BuildingEnergyComparison,
    CompareRequest,
    EnergyPerformanceEstimate,
    PortfolioEnergyProfile,
    RenovationEnergyImpact,
    RenovationImpactRequest,
)
from app.services.energy_performance_service import (
    compare_buildings_energy,
    estimate_energy_class,
    estimate_renovation_impact,
    get_portfolio_energy_profile,
)

router = APIRouter()


@router.get("/buildings/{building_id}/energy-performance", response_model=EnergyPerformanceEstimate)
async def get_energy_performance(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate energy performance class for a building."""
    try:
        return await estimate_energy_class(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/buildings/{building_id}/energy-renovation-impact", response_model=RenovationEnergyImpact)
async def get_renovation_impact(
    building_id: UUID,
    body: RenovationImpactRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Project energy impact of planned interventions."""
    try:
        return await estimate_renovation_impact(db, building_id, body.planned_interventions)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/portfolio/energy-profile", response_model=PortfolioEnergyProfile)
async def get_energy_profile(
    org_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate energy profile across the portfolio."""
    return await get_portfolio_energy_profile(db, org_id)


@router.post("/energy-performance/compare", response_model=list[BuildingEnergyComparison])
async def compare_energy(
    body: CompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare energy performance of up to 10 buildings."""
    try:
        return await compare_buildings_energy(db, body.building_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
