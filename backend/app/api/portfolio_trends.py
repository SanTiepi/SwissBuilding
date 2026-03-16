"""Portfolio Risk Trends API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.portfolio_trends import (
    BuildingRiskTrajectory,
    PortfolioRiskReport,
    PortfolioRiskSnapshot,
    PortfolioRiskTrend,
    RiskHotspot,
)
from app.services.portfolio_risk_trends_service import (
    compare_portfolio_risk_periods,
    get_building_risk_trajectory,
    get_portfolio_risk_report,
    get_portfolio_risk_snapshot,
    get_portfolio_risk_trend,
    get_risk_hotspots,
)

router = APIRouter()


@router.get("/portfolio/risk-trend", response_model=PortfolioRiskTrend)
async def portfolio_risk_trend(
    months: int = Query(12, ge=1, le=120),
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return portfolio-level risk trend over past N months."""
    return await get_portfolio_risk_trend(db, months=months, organization_id=organization_id)


@router.get("/buildings/{building_id}/risk-trajectory", response_model=BuildingRiskTrajectory)
async def building_risk_trajectory(
    building_id: UUID,
    months: int = Query(12, ge=1, le=120),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return risk trajectory for a specific building."""
    return await get_building_risk_trajectory(db, building_id=building_id, months=months)


@router.get("/portfolio/risk-snapshot", response_model=PortfolioRiskSnapshot)
async def portfolio_risk_snapshot(
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return current-state risk distribution across all buildings."""
    return await get_portfolio_risk_snapshot(db, organization_id=organization_id)


@router.get("/portfolio/risk-hotspots", response_model=list[RiskHotspot])
async def portfolio_risk_hotspots(
    limit: int = Query(10, ge=1, le=100),
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return buildings that have been at high/critical risk the longest."""
    return await get_risk_hotspots(db, limit=limit, organization_id=organization_id)


@router.get("/portfolio/risk-report", response_model=PortfolioRiskReport)
async def portfolio_risk_report(
    months: int = Query(12, ge=1, le=120),
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return full portfolio risk report."""
    return await get_portfolio_risk_report(db, months=months, organization_id=organization_id)


@router.get("/portfolio/risk-comparison")
async def portfolio_risk_comparison(
    period1_start: date = Query(...),
    period1_end: date = Query(...),
    period2_start: date = Query(...),
    period2_end: date = Query(...),
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare risk metrics between two time periods."""
    return await compare_portfolio_risk_periods(
        db,
        period1_start=period1_start,
        period1_end=period1_end,
        period2_start=period2_start,
        period2_end=period2_end,
        organization_id=organization_id,
    )
