"""Quality assurance API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.quality_assurance import (
    PortfolioQualityReport,
    QARunResult,
    QualityScoreResult,
    QualityTrendsResult,
)
from app.services.quality_assurance_service import (
    get_portfolio_quality_report,
    get_quality_score,
    get_quality_trends,
    run_quality_checks,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/quality-assurance/checks",
    response_model=QARunResult,
)
async def run_qa_checks_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Run comprehensive QA checks on a building."""
    result = await run_quality_checks(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/quality-assurance/score",
    response_model=QualityScoreResult,
)
async def get_qa_score_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get weighted quality score for a building."""
    result = await get_quality_score(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/quality-assurance/trends",
    response_model=QualityTrendsResult,
)
async def get_qa_trends_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get quality score trends for a building."""
    result = await get_quality_trends(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/quality-assurance/report",
    response_model=PortfolioQualityReport,
)
async def get_portfolio_qa_report_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level quality report for an organization."""
    result = await get_portfolio_quality_report(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
