"""
SwissBuildingOS - Insurance Risk Assessment API

4 endpoints for insurance risk evaluation of pollutant-containing buildings.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.insurance_risk_assessment import (
    InsuranceCompareRequest,
    InsuranceCompareResponse,
    InsuranceRiskAssessment,
    LiabilityExposure,
    PortfolioInsuranceSummary,
)
from app.services.insurance_risk_assessment_service import (
    assess_building_insurance_risk,
    compare_insurance_profiles,
    get_liability_exposure,
    get_portfolio_insurance_summary,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/insurance-risk",
    response_model=InsuranceRiskAssessment,
)
async def get_insurance_risk(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Complete insurance risk assessment for a building."""
    try:
        return await assess_building_insurance_risk(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/liability-exposure",
    response_model=LiabilityExposure,
)
async def get_building_liability_exposure(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze liability exposure across 4 categories."""
    try:
        return await get_liability_exposure(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post(
    "/insurance/compare",
    response_model=InsuranceCompareResponse,
)
async def compare_insurance(
    data: InsuranceCompareRequest,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare insurance profiles across multiple buildings."""
    return await compare_insurance_profiles(db, data.building_ids)


@router.get(
    "/organizations/{org_id}/insurance-summary",
    response_model=PortfolioInsuranceSummary,
)
async def get_org_insurance_summary(
    org_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level insurance summary for an organization."""
    return await get_portfolio_insurance_summary(db, org_id)
