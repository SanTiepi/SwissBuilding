"""ControlTower v2 — Unified action feed API."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.action_feed import ActionFeedResponse, ActionFeedSummary
from app.services.action_aggregation_service import get_action_feed, get_feed_summary

router = APIRouter()


@router.get(
    "/control-tower/actions",
    response_model=ActionFeedResponse,
    tags=["Control Tower"],
)
async def list_actions(
    building_id: UUID | None = Query(None),
    org_id: UUID | None = Query(None),
    priority: int | None = Query(None, ge=0, le=4),
    source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("actions", "list")),
    db: AsyncSession = Depends(get_db),
) -> ActionFeedResponse:
    """Aggregated, priority-sorted action feed from all sources."""
    return await get_action_feed(
        db,
        current_user.id,
        building_id=building_id,
        organization_id=org_id,
        priority_min=priority,
        priority_max=priority,
        source_type=source,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/control-tower/summary",
    response_model=ActionFeedSummary,
    tags=["Control Tower"],
)
async def feed_summary(
    current_user: User = Depends(require_permission("actions", "read")),
    db: AsyncSession = Depends(get_db),
) -> ActionFeedSummary:
    """Counts per priority level and source type."""
    return await get_feed_summary(db, current_user.id)
