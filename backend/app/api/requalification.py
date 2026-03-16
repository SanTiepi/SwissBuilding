"""Requalification replay timeline API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.requalification import (
    RequalificationRecommendation,
    RequalificationTimeline,
    RequalificationTriggerReport,
)
from app.services.requalification_service import (
    detect_requalification_triggers,
    get_requalification_recommendations,
    get_requalification_timeline,
    get_state_change_summary,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/requalification/timeline",
    response_model=RequalificationTimeline,
)
async def get_timeline_endpoint(
    building_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the requalification replay timeline for a building."""
    await _get_building_or_404(db, building_id)
    return await get_requalification_timeline(db, building_id, limit=limit)


@router.get(
    "/buildings/{building_id}/requalification/summary",
)
async def get_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a compact state-change summary for a building."""
    await _get_building_or_404(db, building_id)
    return await get_state_change_summary(db, building_id)


@router.get(
    "/buildings/{building_id}/requalification/triggers",
    response_model=RequalificationTriggerReport,
)
async def get_triggers_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect requalification triggers for a building."""
    await _get_building_or_404(db, building_id)
    return await detect_requalification_triggers(db, building_id)


@router.get(
    "/buildings/{building_id}/requalification/recommendations",
    response_model=list[RequalificationRecommendation],
)
async def get_recommendations_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get actionable requalification recommendations for a building."""
    await _get_building_or_404(db, building_id)
    return await get_requalification_recommendations(db, building_id)
