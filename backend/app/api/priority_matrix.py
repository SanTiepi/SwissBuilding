"""Priority Matrix API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.priority_matrix import (
    CriticalPath,
    PortfolioPriorityOverview,
    PriorityMatrix,
    QuickWins,
)
from app.services.priority_matrix_service import (
    build_priority_matrix,
    get_critical_path_items,
    get_portfolio_priority_overview,
    suggest_quick_wins,
)

router = APIRouter()


@router.get("/buildings/{building_id}/priority-matrix", response_model=PriorityMatrix)
async def get_building_priority_matrix(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get Eisenhower-style urgency x impact priority matrix for a building."""
    try:
        return await build_priority_matrix(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/critical-path", response_model=CriticalPath)
async def get_building_critical_path(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get critical path items: urgent + critical quadrant with dependencies."""
    try:
        return await get_critical_path_items(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/priority-quick-wins", response_model=QuickWins)
async def get_building_quick_wins(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get quick wins: low-effort, high-impact items doable in <1 week."""
    try:
        return await suggest_quick_wins(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/priority-overview",
    response_model=PortfolioPriorityOverview,
)
async def get_org_priority_overview(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level priority matrix aggregation for an organization."""
    return await get_portfolio_priority_overview(db, org_id)
