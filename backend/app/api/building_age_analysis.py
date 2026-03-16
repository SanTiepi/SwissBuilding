"""Building age analysis API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_age_analysis import (
    AgeBasedRiskProfile,
    EraClassification,
    EraHotspotReport,
    PortfolioAgeDistribution,
)
from app.services.building_age_analysis_service import (
    analyze_construction_era,
    get_age_based_risk_profile,
    get_portfolio_age_distribution,
    identify_era_specific_hotspots,
)

router = APIRouter()


@router.get("/buildings/{building_id}/age-analysis", response_model=EraClassification)
async def get_era_classification(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get era classification and pollutant probability for a building."""
    try:
        return await analyze_construction_era(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/age-risk-profile", response_model=AgeBasedRiskProfile)
async def get_building_age_risk_profile(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get age-based risk profile with modifiers for a building."""
    try:
        return await get_age_based_risk_profile(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/age-hotspots", response_model=EraHotspotReport)
async def get_era_hotspots(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get era-specific pollutant hotspots mapped to building zones."""
    try:
        return await identify_era_specific_hotspots(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/organizations/{org_id}/age-distribution", response_model=PortfolioAgeDistribution)
async def get_org_age_distribution(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio age distribution for an organization."""
    return await get_portfolio_age_distribution(db, org_id)
