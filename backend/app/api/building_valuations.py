"""Building valuation API routes — pollutant impact on Swiss building value."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_valuation import (
    MarketPositionResponse,
    PollutantImpactResponse,
    PortfolioValuationSummary,
    RenovationROIResponse,
)
from app.services.building_valuation_service import (
    calculate_renovation_roi,
    compare_market_position,
    estimate_pollutant_impact,
    get_portfolio_valuation_summary,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/valuation-impact",
    response_model=PollutantImpactResponse,
)
async def get_valuation_impact(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate pollutant impact on building valuation."""
    try:
        return await estimate_pollutant_impact(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/valuation-roi",
    response_model=RenovationROIResponse,
)
async def get_valuation_roi(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Calculate renovation ROI for pollutant remediation."""
    try:
        return await calculate_renovation_roi(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/valuation-market-position",
    response_model=MarketPositionResponse,
)
async def get_valuation_market_position(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare building's pollutant profile against similar buildings."""
    try:
        return await compare_market_position(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/valuation-summary",
    response_model=PortfolioValuationSummary,
)
async def get_org_valuation_summary(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-wide valuation impact summary for an organization."""
    try:
        return await get_portfolio_valuation_summary(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
