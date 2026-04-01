"""Portfolio Risk API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.portfolio_risk import (
    BuildingRiskPointRead,
    PortfolioRiskOverviewRead,
)
from app.services.portfolio_risk_service import (
    get_portfolio_risk_overview,
    get_risk_heatmap_data,
)

router = APIRouter()


@router.get(
    "/portfolio/risk-overview",
    response_model=PortfolioRiskOverviewRead,
)
async def portfolio_risk_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full portfolio risk overview with evidence scores, action counts, and distribution."""
    org_id = current_user.organization_id
    if org_id is None:
        return {
            "total_buildings": 0,
            "avg_evidence_score": 0.0,
            "buildings_at_risk": 0,
            "buildings_ok": 0,
            "worst_building_id": None,
            "distribution": {
                "grade_a": 0,
                "grade_b": 0,
                "grade_c": 0,
                "grade_d": 0,
                "grade_f": 0,
            },
            "buildings": [],
        }

    return await get_portfolio_risk_overview(db, org_id)


@router.get(
    "/portfolio/risk-heatmap",
    response_model=list[BuildingRiskPointRead],
)
async def portfolio_risk_heatmap(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Minimal building data points for map rendering, scoped to user's org."""
    org_id = current_user.organization_id
    if org_id is None:
        return []

    return await get_risk_heatmap_data(db, org_id)
