"""BatiConnect — DefectShield API: construction defect deadline management.

Art. 367 al. 1bis CO: 60-day notification window since 01.01.2026.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.defect_timeline import (
    DefectAlertResponse,
    DefectTimelineCreate,
    DefectTimelineResponse,
)
from app.services.defect_timeline_service import (
    create_timeline,
    get_active_alerts,
    get_timeline,
    list_building_timelines,
    update_timeline_status,
)

router = APIRouter()


@router.post("/defects/timeline", response_model=DefectTimelineResponse, status_code=201)
async def create_defect_timeline(
    data: DefectTimelineCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new defect timeline entry with computed deadlines."""
    from app.services.building_service import get_building

    building = await get_building(db, data.building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    timeline = await create_timeline(db, data)
    return timeline


@router.get("/defects/timeline/{building_id}", response_model=list[DefectTimelineResponse])
async def list_defect_timelines(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all defect timelines for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await list_building_timelines(db, building_id)


@router.get("/defects/alerts", response_model=list[DefectAlertResponse])
async def list_defect_alerts(
    days_threshold: int = Query(45, ge=1, le=365),
    building_id: UUID | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get cross-building active alerts for defects nearing notification deadline."""
    return await get_active_alerts(db, days_threshold=days_threshold, building_id=building_id)


@router.post("/defects/notification/{timeline_id}", response_model=DefectTimelineResponse)
async def generate_notification(
    timeline_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Generate notification letter for a defect (stub: marks as notified, returns JSON).

    Future: will generate PDF via Gotenberg and store in MinIO.
    """
    from datetime import UTC, datetime

    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Defect timeline not found")
    if timeline.status != "active":
        raise HTTPException(status_code=400, detail=f"Cannot notify a defect with status '{timeline.status}'")

    updated = await update_timeline_status(
        db,
        timeline_id,
        status="notified",
        notified_at=datetime.now(UTC),
    )
    return updated
