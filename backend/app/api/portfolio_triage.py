"""Portfolio triage API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.instant_card import InstantCardResult
from app.schemas.portfolio_triage import PortfolioTriageResult
from app.services.instant_card_service import build_instant_card
from app.services.portfolio_triage_service import get_portfolio_triage

router = APIRouter()


@router.get(
    "/organizations/{org_id}/portfolio-triage",
    response_model=PortfolioTriageResult,
)
async def portfolio_triage(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio triage for an organization — classifies buildings by urgency."""
    try:
        return await get_portfolio_triage(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/instant-card",
    response_model=InstantCardResult,
)
async def get_instant_card(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the full decision-grade instant card for a building."""
    result = await build_instant_card(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
