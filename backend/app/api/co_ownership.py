"""Co-ownership governance API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.co_ownership import (
    BuildingCoOwnershipInfo,
    BuildingDecisionLog,
    PortfolioCoOwnershipSummary,
    RemediationCostSplit,
)
from app.services.co_ownership_service import (
    calculate_remediation_cost_split,
    get_building_co_ownership_info,
    get_building_decision_log,
    get_portfolio_co_ownership_summary,
)

router = APIRouter()


@router.get(
    "/co-ownership/buildings/{building_id}/info",
    response_model=BuildingCoOwnershipInfo,
)
async def building_co_ownership_info(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get co-ownership structure for a building."""
    return await get_building_co_ownership_info(building_id, db)


@router.get(
    "/co-ownership/buildings/{building_id}/cost-split",
    response_model=RemediationCostSplit,
)
async def building_cost_split(
    building_id: UUID,
    method: str = Query(default="by_share"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Calculate remediation cost split across co-owners."""
    return await calculate_remediation_cost_split(building_id, db, method=method)


@router.get(
    "/co-ownership/buildings/{building_id}/decisions",
    response_model=BuildingDecisionLog,
)
async def building_decisions(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get decision log for a building's co-ownership."""
    return await get_building_decision_log(building_id, db)


@router.get(
    "/co-ownership/organizations/{org_id}/summary",
    response_model=PortfolioCoOwnershipSummary,
)
async def org_co_ownership_summary(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level co-ownership summary for an organization."""
    return await get_portfolio_co_ownership_summary(org_id, db)
