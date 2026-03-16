"""
SwissBuildingOS - Occupant Safety API

4 GET endpoints for occupant safety evaluation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.occupant_safety import (
    BuildingExposureRisk,
    BuildingSafetyRecommendations,
    OccupantSafetyAssessment,
    PortfolioSafetyOverview,
)
from app.services.occupant_safety_service import (
    evaluate_occupant_safety,
    generate_safety_recommendations,
    get_exposure_risk_by_zone,
    get_portfolio_safety_overview,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/occupant-safety",
    response_model=OccupantSafetyAssessment,
)
async def get_occupant_safety(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Overall occupant safety assessment for a building."""
    try:
        return await evaluate_occupant_safety(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/exposure-risk",
    response_model=BuildingExposureRisk,
)
async def get_exposure_risk(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detailed exposure risk per zone."""
    try:
        return await get_exposure_risk_by_zone(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/safety-recommendations",
    response_model=BuildingSafetyRecommendations,
)
async def get_safety_recommendations(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Prioritized safety recommendations for a building."""
    try:
        return await generate_safety_recommendations(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/organizations/{org_id}/safety-overview",
    response_model=PortfolioSafetyOverview,
)
async def get_org_safety_overview(
    org_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level safety overview for an organization."""
    try:
        return await get_portfolio_safety_overview(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
