"""BatiConnect — DefectShield API: construction defect deadline management.

Art. 367 al. 1bis CO: 60-day notification window since 01.01.2026.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.defect_timeline import (
    DefectAlertResponse,
    DefectTimelineCreate,
    DefectTimelineResponse,
    DefectTimelineUpdate,
)
from app.services.defect_timeline_service import (
    VALID_STATUS_TRANSITIONS,
    create_timeline,
    get_active_alerts,
    get_timeline,
    list_building_timelines,
    update_defect_status,
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

    # Fire alert if deadline is already approaching or passed
    from app.services.defect_alert_service import check_deadline_on_create

    await check_deadline_on_create(db, timeline, user_id=current_user.id)
    await db.commit()

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


@router.get("/defects/timelines/{timeline_id}", response_model=DefectTimelineResponse)
async def get_defect_timeline(
    timeline_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single defect timeline by ID."""
    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Defect timeline not found")
    return timeline


@router.patch("/defects/timelines/{timeline_id}", response_model=DefectTimelineResponse)
async def patch_defect_timeline(
    timeline_id: UUID,
    data: DefectTimelineUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update defect timeline status with validated state transitions.

    Valid transitions: active→{notified,expired,resolved}, notified→resolved,
    expired→resolved. 'resolved' is terminal.
    """
    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Defect timeline not found")

    if data.status and data.status != timeline.status:
        allowed = VALID_STATUS_TRANSITIONS.get(timeline.status, set())
        if data.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid transition: {timeline.status} → {data.status}. "
                    f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
                ),
            )
        try:
            kwargs = {}
            if data.notified_at is not None:
                kwargs["notified_at"] = data.notified_at
            if data.notification_pdf_url is not None:
                kwargs["notification_pdf_url"] = data.notification_pdf_url
            if data.description is not None:
                kwargs["description"] = data.description
            timeline = await update_defect_status(db, timeline_id, data.status, **kwargs)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        # Fire alert notification on state change
        from app.services.defect_alert_service import on_status_change

        await on_status_change(db, timeline, data.status, current_user.id)
        await db.commit()
    elif data.description is not None:
        # Allow updating description without status change
        timeline.description = data.description
        await db.commit()
        await db.refresh(timeline)

    return timeline


@router.delete("/defects/timelines/{timeline_id}", status_code=200)
async def delete_defect_timeline(
    timeline_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a defect timeline (mark as deleted, don't remove)."""
    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Defect timeline not found")

    timeline.status = "deleted"
    await db.commit()
    return {"detail": "Defect timeline soft-deleted", "id": str(timeline_id)}


@router.get("/defects/alerts", response_model=list[DefectAlertResponse])
async def list_defect_alerts(
    days_threshold: int = Query(45, ge=1, le=365),
    building_id: UUID | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get cross-building active alerts for defects nearing notification deadline."""
    return await get_active_alerts(db, days_threshold=days_threshold, building_id=building_id)


@router.post("/defects/{timeline_id}/generate-letter")
async def generate_defect_letter(
    timeline_id: UUID,
    lang: Literal["fr", "de", "it"] = Query("fr"),
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a PDF notification letter for a defect via Gotenberg.

    Art. 367 al. 1bis CO: formal defect notification letter with
    building address, EGID, defect description, discovery date,
    notification deadline, legal reference, and signature blocks.

    Also marks the defect as notified and stores the PDF URL.
    """
    import logging
    from datetime import UTC, datetime

    from app.services.defect_letter_service import generate_letter_pdf

    logger = logging.getLogger(__name__)

    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Defect timeline not found")
    if timeline.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate letter for a defect with status '{timeline.status}'",
        )

    try:
        pdf_bytes = await generate_letter_pdf(db, timeline_id, lang=lang)
    except Exception as exc:
        logger.exception("Failed to generate defect letter PDF: %s", exc)
        raise HTTPException(status_code=502, detail="PDF generation failed") from exc

    # Mark as notified
    filename = f"defect-notification-{timeline_id}-{lang}.pdf"
    await update_timeline_status(
        db,
        timeline_id,
        status="notified",
        notified_at=datetime.now(UTC),
        notification_pdf_url=filename,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
