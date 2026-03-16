from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.portfolio_summary import PortfolioCompareRequest, PortfolioSummary
from app.services.portfolio_summary_service import (
    get_portfolio_comparison,
    get_portfolio_health_score,
    get_portfolio_summary,
)

router = APIRouter()


@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def portfolio_summary_endpoint(
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return a full portfolio summary combining all dimensions."""
    return await get_portfolio_summary(db, organization_id=organization_id)


@router.post("/portfolio/compare", response_model=list[PortfolioSummary])
async def portfolio_compare_endpoint(
    body: PortfolioCompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare portfolio summaries across organizations."""
    return await get_portfolio_comparison(db, org_ids=body.organization_ids)


@router.get("/portfolio/health-score")
async def portfolio_health_score_endpoint(
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return a single 0-100 health score with breakdown by dimension."""
    return await get_portfolio_health_score(db, organization_id=organization_id)
