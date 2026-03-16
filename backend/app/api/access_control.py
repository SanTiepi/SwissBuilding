"""
SwissBuildingOS - Access Control API

4 GET endpoints for building access restrictions and permit requirements.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.access_control import (
    BuildingAccessRestrictions,
    BuildingPermitRequirements,
    BuildingSafeZones,
    PortfolioAccessStatus,
)
from app.services.access_control_service import (
    generate_access_permit_requirements,
    generate_access_restrictions,
    get_portfolio_access_status,
    get_safe_zones,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/access-restrictions",
    response_model=BuildingAccessRestrictions,
)
async def get_access_restrictions(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Per-zone access rules based on pollutant status."""
    try:
        return await generate_access_restrictions(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/safe-zones",
    response_model=BuildingSafeZones,
)
async def get_building_safe_zones(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Zones confirmed safe for unrestricted access."""
    try:
        return await get_safe_zones(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/access-permits",
    response_model=BuildingPermitRequirements,
)
async def get_access_permits(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Permits and authorizations needed to enter restricted zones."""
    try:
        return await generate_access_permit_requirements(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/organizations/{org_id}/access-status",
    response_model=PortfolioAccessStatus,
)
async def get_org_access_status(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level access compliance overview for an organization."""
    try:
        return await get_portfolio_access_status(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
