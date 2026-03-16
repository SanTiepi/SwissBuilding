"""Contractor matching endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.contractor_matching import (
    ContractorMatchResult,
    ContractorNeedsResult,
    PortfolioContractorDemandResult,
    RequiredCertificationsResult,
)
from app.services.contractor_matching_service import (
    estimate_contractor_needs,
    get_portfolio_contractor_demand,
    get_required_certifications,
    match_contractors,
)

router = APIRouter()


@router.get("/buildings/{building_id}/contractor-matching", response_model=ContractorMatchResult)
async def get_contractor_matching(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Rank contractor organizations by fit for a building."""
    return await match_contractors(db, building_id)


@router.get("/buildings/{building_id}/required-certifications", response_model=RequiredCertificationsResult)
async def get_building_required_certifications(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Derive required certifications from building diagnostics."""
    return await get_required_certifications(db, building_id)


@router.get("/buildings/{building_id}/contractor-needs", response_model=ContractorNeedsResult)
async def get_building_contractor_needs(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate workforce sizing for a building."""
    return await estimate_contractor_needs(db, building_id)


@router.get("/organizations/{org_id}/contractor-demand", response_model=PortfolioContractorDemandResult)
async def get_org_contractor_demand(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate contractor demand across an organization's buildings."""
    return await get_portfolio_contractor_demand(db, org_id)
