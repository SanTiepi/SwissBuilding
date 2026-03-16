from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.event import EventCreate, EventRead
from app.services.audit_service import log_action

router = APIRouter()


@router.get("/buildings/{building_id}/events", response_model=list[EventRead])
async def list_events_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("events", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all events for a building, sorted by date descending."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from sqlalchemy import select

    from app.models.event import Event

    result = await db.execute(select(Event).where(Event.building_id == building_id).order_by(Event.date.desc()))
    events = result.scalars().all()
    return events


@router.post("/buildings/{building_id}/events", response_model=EventRead, status_code=201)
async def create_event_endpoint(
    building_id: UUID,
    data: EventCreate,
    current_user: User = Depends(require_permission("events", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new event for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    from app.models.event import Event

    event = Event(building_id=building_id, created_by=current_user.id, **data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    await log_action(db, current_user.id, "create", "event", event.id)
    return event
