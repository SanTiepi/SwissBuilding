"""
SwissBuildingOS - Tenant Impact API

4 GET endpoints for tenant impact assessment during remediation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.tenant_impact import (
    DisplacementCostEstimate,
    PortfolioTenantExposure,
    TenantCommunicationPlan,
    TenantImpactAssessment,
)
from app.services.tenant_impact_service import (
    assess_tenant_impact,
    estimate_displacement_costs,
    generate_tenant_communication_plan,
    get_portfolio_tenant_exposure,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/tenant-impact",
    response_model=TenantImpactAssessment,
)
async def get_tenant_impact(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Assess tenant impact during remediation for a building."""
    try:
        return await assess_tenant_impact(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/tenant-communication-plan",
    response_model=TenantCommunicationPlan,
)
async def get_tenant_communication_plan(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate tenant notification timeline for a building."""
    try:
        return await generate_tenant_communication_plan(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/displacement-costs",
    response_model=DisplacementCostEstimate,
)
async def get_displacement_costs(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate displacement costs for a building's tenants."""
    try:
        return await estimate_displacement_costs(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/organizations/{org_id}/tenant-exposure",
    response_model=PortfolioTenantExposure,
)
async def get_org_tenant_exposure(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level tenant exposure overview for an organization."""
    try:
        return await get_portfolio_tenant_exposure(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
