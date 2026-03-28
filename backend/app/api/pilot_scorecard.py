"""BatiConnect -- Pilot Scorecard API routes.

G2 pilot conversion endpoints:
  GET /pilot/scorecard         -- org-level pilot scorecard
  GET /buildings/{id}/scorecard -- per-building scorecard
  GET /pilot/weekly-summary    -- weekly operator ritual summary
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.pilot_scorecard_service import (
    get_building_scorecard,
    get_pilot_scorecard,
    get_weekly_summary,
)

router = APIRouter()


@router.get("/pilot/scorecard")
async def pilot_scorecard(
    baseline_date: date | None = Query(None, description="Start date for the pilot period"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate pilot scorecard for the current user's organization."""
    org_id = getattr(current_user, "organization_id", None)
    if org_id is None:
        return {"error": "no_organization", "detail": "L'utilisateur n'est pas rattache a une organisation."}
    return await get_pilot_scorecard(db, org_id, baseline_date=baseline_date)


@router.get("/buildings/{building_id}/scorecard")
async def building_scorecard(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get per-building pilot scorecard with before/after metrics."""
    return await get_building_scorecard(db, building_id)


@router.get("/pilot/weekly-summary")
async def weekly_summary(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Weekly summary for the operator ritual (rituel hebdo)."""
    org_id = getattr(current_user, "organization_id", None)
    if org_id is None:
        return {"error": "no_organization", "detail": "L'utilisateur n'est pas rattache a une organisation."}
    return await get_weekly_summary(db, org_id)
