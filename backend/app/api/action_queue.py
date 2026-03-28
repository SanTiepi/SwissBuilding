"""BatiConnect - Action Queue API routes."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.action_item import ActionItemRead
from app.services.action_queue_service import (
    complete_action,
    get_building_queue,
    get_weekly_summary,
    snooze_action,
)
from app.services.audit_service import log_action

router = APIRouter()


class CompleteRequest(BaseModel):
    resolution_note: str | None = None


class SnoozeRequest(BaseModel):
    snooze_until: date


@router.get("/buildings/{building_id}/action-queue")
async def get_action_queue(
    building_id: UUID,
    status: str = Query("open", description="Filter: open, done, all"),
    current_user: User = Depends(require_permission("actions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Get the prioritized action queue for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_building_queue(db, building_id, filter_status=status)


@router.post("/actions/{action_id}/complete", response_model=ActionItemRead)
async def complete_action_endpoint(
    action_id: UUID,
    body: CompleteRequest | None = None,
    current_user: User = Depends(require_permission("actions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Complete an action and trigger re-evaluation of generators."""
    note = body.resolution_note if body else None
    action = await complete_action(db, action_id, current_user.id, note)
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    await log_action(db, current_user.id, "complete", "action_item", action_id)
    return action


@router.post("/actions/{action_id}/snooze", response_model=ActionItemRead)
async def snooze_action_endpoint(
    action_id: UUID,
    body: SnoozeRequest,
    current_user: User = Depends(require_permission("actions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Snooze an action to a future date."""
    action = await snooze_action(db, action_id, body.snooze_until, current_user.id)
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    await log_action(db, current_user.id, "snooze", "action_item", action_id)
    return action


@router.get("/buildings/{building_id}/weekly-summary")
async def get_weekly_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("actions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Get a weekly summary of action activity for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_weekly_summary(db, building_id)
