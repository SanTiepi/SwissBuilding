"""Environmental impact API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.environmental_impact import (
    EnvironmentalImpactAssessment,
    GreenBuildingScore,
    PortfolioEnvironmentalReport,
    RemediationFootprint,
)
from app.services.environmental_impact_service import (
    assess_environmental_impact,
    calculate_green_building_score,
    estimate_remediation_environmental_footprint,
    get_portfolio_environmental_report,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/environmental-impact",
    response_model=EnvironmentalImpactAssessment,
)
async def get_environmental_impact(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Assess environmental risk from building pollutants."""
    try:
        return await assess_environmental_impact(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/remediation-footprint",
    response_model=RemediationFootprint,
)
async def get_remediation_footprint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate the environmental footprint of remediation works."""
    try:
        return await estimate_remediation_environmental_footprint(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/green-score",
    response_model=GreenBuildingScore,
)
async def get_green_score(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Calculate composite green building score."""
    try:
        return await calculate_green_building_score(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/portfolio/environmental-report",
    response_model=PortfolioEnvironmentalReport,
)
async def get_environmental_report(
    org_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get organization-level environmental report."""
    return await get_portfolio_environmental_report(db, org_id)
