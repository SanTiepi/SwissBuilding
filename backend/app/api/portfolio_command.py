"""Portfolio Command Center API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.portfolio_command_service import (
    get_portfolio_heatmap,
    get_portfolio_overview,
)

router = APIRouter()


@router.get("/portfolio/command")
async def portfolio_command_overview(
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return full director-level portfolio overview."""
    return await get_portfolio_overview(db, org_id=organization_id)


@router.get("/portfolio/heatmap")
async def portfolio_heatmap(
    organization_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return heatmap data for readiness matrix."""
    return await get_portfolio_heatmap(db, org_id=organization_id)
