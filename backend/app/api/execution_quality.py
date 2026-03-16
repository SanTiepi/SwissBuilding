"""Execution quality API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.execution_quality import (
    AcceptanceCriteria,
    BuildingAcceptanceReport,
    InterventionQualityReport,
    PortfolioQualityDashboard,
)
from app.services.execution_quality_service import (
    evaluate_intervention_quality,
    get_acceptance_criteria,
    get_building_acceptance_report,
    get_portfolio_quality_dashboard,
)

router = APIRouter()


@router.get(
    "/execution-quality/interventions/{intervention_id}/report",
    response_model=InterventionQualityReport,
)
async def get_intervention_quality_report(
    intervention_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate execution quality for an intervention."""
    result = await evaluate_intervention_quality(intervention_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return result


@router.get(
    "/execution-quality/pollutants/{pollutant_type}/criteria",
    response_model=list[AcceptanceCriteria],
)
async def get_pollutant_acceptance_criteria(
    pollutant_type: str,
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """Get Swiss regulatory acceptance criteria for a pollutant type."""
    return await get_acceptance_criteria(pollutant_type)


@router.get(
    "/execution-quality/buildings/{building_id}/acceptance",
    response_model=BuildingAcceptanceReport,
)
async def get_building_acceptance_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get acceptance report for a building's interventions."""
    result = await get_building_acceptance_report(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/execution-quality/organizations/{org_id}/dashboard",
    response_model=PortfolioQualityDashboard,
)
async def get_org_quality_dashboard(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio quality dashboard for an organization."""
    result = await get_portfolio_quality_dashboard(org_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
