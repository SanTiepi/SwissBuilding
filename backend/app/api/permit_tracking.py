"""Permit tracking API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.permit_tracking import (
    PermitDependencyResponse,
    PermitStatusResponse,
    PortfolioPermitOverview,
    RequiredPermitsResponse,
)
from app.services.permit_tracking_service import (
    get_permit_dependencies,
    get_portfolio_permit_overview,
    get_required_permits,
    track_permit_status,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/permits/required",
    response_model=RequiredPermitsResponse,
)
async def get_building_required_permits(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get list of permits required for a building based on its current state."""
    try:
        return await get_required_permits(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/permits/status",
    response_model=PermitStatusResponse,
)
async def get_building_permit_status(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Track current status of each permit for a building."""
    try:
        return await track_permit_status(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/permits/dependencies",
    response_model=PermitDependencyResponse,
)
async def get_building_permit_dependencies(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get permit dependency graph for a building."""
    try:
        return await get_permit_dependencies(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/permits/overview",
    response_model=PortfolioPermitOverview,
)
async def get_org_permit_overview(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get organization-level permit overview across all buildings."""
    try:
        return await get_portfolio_permit_overview(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
