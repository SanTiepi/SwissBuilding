from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.timeline import TimelineResponse
from app.services.building_service import get_building
from app.services.timeline_service import get_building_timeline

router = APIRouter()


@router.get("/buildings/{building_id}/timeline", response_model=TimelineResponse)
async def get_building_timeline_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    event_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get unified building timeline with all events sorted chronologically."""
    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    items, total = await get_building_timeline(db, building_id, page=page, size=size, event_type_filter=event_type)
    pages = (total + size - 1) // size if total > 0 else 0
    return TimelineResponse(items=items, total=total, page=page, size=size, pages=pages)
