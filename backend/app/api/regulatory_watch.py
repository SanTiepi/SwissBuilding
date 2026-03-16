"""Regulatory Watch API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.regulatory_watch import (
    ActiveRegulationsResponse,
    PortfolioExposureResponse,
    RegulatoryImpactResponse,
    ThresholdSimulationResponse,
)
from app.services.regulatory_watch_service import (
    assess_regulatory_impact,
    get_active_regulations,
    get_portfolio_regulatory_exposure,
    simulate_threshold_change,
)

router = APIRouter()


@router.get(
    "/regulatory-watch/regulations",
    response_model=ActiveRegulationsResponse,
)
async def list_active_regulations(
    canton: str = Query(..., min_length=2, max_length=2, description="Canton code (e.g. VD, GE)"),
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List active regulations applicable to a canton."""
    regulations = await get_active_regulations(canton, db)
    return {"canton": canton.upper(), "regulations": regulations}


@router.get(
    "/regulatory-watch/buildings/{building_id}/impact",
    response_model=RegulatoryImpactResponse,
)
async def get_regulatory_impact(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Assess impact of current regulations on a building."""
    try:
        return await assess_regulatory_impact(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/regulatory-watch/buildings/{building_id}/simulate",
    response_model=ThresholdSimulationResponse,
)
async def simulate_threshold(
    building_id: UUID,
    pollutant_type: str = Query(..., description="Pollutant type (asbestos, pcb, lead, hap, radon)"),
    new_threshold: float = Query(..., gt=0, description="New threshold value to simulate"),
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate a threshold change for a building."""
    try:
        return await simulate_threshold_change(building_id, pollutant_type, new_threshold, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/regulatory-watch/portfolio/{org_id}/exposure",
    response_model=PortfolioExposureResponse,
)
async def get_portfolio_exposure(
    org_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get org-wide regulatory exposure summary."""
    return await get_portfolio_regulatory_exposure(org_id, db)
