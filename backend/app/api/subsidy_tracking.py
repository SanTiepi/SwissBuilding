"""Subsidy tracking API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.subsidy_tracking import (
    BuildingFundingGapAnalysis,
    BuildingSubsidyEligibility,
    BuildingSubsidyStatus,
    PortfolioSubsidySummary,
)
from app.services.subsidy_tracking_service import (
    analyze_funding_gap,
    get_building_subsidy_eligibility,
    get_building_subsidy_status,
    get_portfolio_subsidy_summary,
)

router = APIRouter()


@router.get(
    "/subsidy-tracking/buildings/{building_id}/eligibility",
    response_model=BuildingSubsidyEligibility,
)
async def get_eligibility(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Check which subsidy programs a building qualifies for."""
    try:
        return await get_building_subsidy_eligibility(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/subsidy-tracking/buildings/{building_id}/status",
    response_model=BuildingSubsidyStatus,
)
async def get_status(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get subsidy application status for a building."""
    try:
        return await get_building_subsidy_status(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/subsidy-tracking/buildings/{building_id}/funding-gap",
    response_model=BuildingFundingGapAnalysis,
)
async def get_funding_gap(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze funding gap between remediation costs and available subsidies."""
    try:
        return await analyze_funding_gap(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/subsidy-summary",
    response_model=PortfolioSubsidySummary,
)
async def get_org_subsidy_summary(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level subsidy summary for an organization."""
    try:
        return await get_portfolio_subsidy_summary(org_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
