from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.timeline_enrichment import EnrichedTimeline
from app.services.building_service import get_building
from app.services.timeline_enrichment_service import (
    get_enriched_timeline,
    get_lifecycle_summary,
)

router = APIRouter()


@router.get("/buildings/{building_id}/timeline/enriched", response_model=EnrichedTimeline)
async def get_enriched_timeline_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    event_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get enriched building timeline with lifecycle phases, importance, and links."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_enriched_timeline(db, building_id, page=page, size=size, event_type_filter=event_type)


@router.get("/buildings/{building_id}/timeline/lifecycle-summary", response_model=dict[str, int])
async def get_lifecycle_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get lifecycle phase counts for a building's timeline."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_lifecycle_summary(db, building_id)
