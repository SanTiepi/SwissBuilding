"""Cross-Layer Intelligence API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.cross_layer_intelligence import (
    CrossLayerInsightRead,
    IntelligenceSummaryRead,
    PortfolioInsightRead,
)
from app.services.cross_layer_intelligence import (
    detect_cross_layer_insights,
    detect_portfolio_insights,
    get_intelligence_summary,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/intelligence",
    response_model=list[CrossLayerInsightRead],
)
async def get_building_intelligence(
    building_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cross-layer intelligence insights for a building."""
    insights = await detect_cross_layer_insights(db, building_id)
    if insights is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return insights


@router.get(
    "/portfolio/intelligence",
    response_model=list[PortfolioInsightRead],
)
async def get_portfolio_intelligence(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level intelligence insights for the user's organization."""
    if not current_user.organization_id:
        return []
    return await detect_portfolio_insights(db, current_user.organization_id)


@router.get(
    "/intelligence/summary",
    response_model=IntelligenceSummaryRead,
)
async def get_summary(
    building_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated intelligence summary (building or portfolio scope)."""
    org_id = current_user.organization_id if not building_id else None
    return await get_intelligence_summary(db, building_id=building_id, org_id=org_id)
