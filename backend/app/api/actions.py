from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.action_item import ActionItemCreate, ActionItemRead, ActionItemUpdate
from app.services.action_service import (
    create_action,
    list_actions,
    list_building_actions,
    update_action,
)
from app.services.audit_service import log_action

router = APIRouter()


@router.get("/actions", response_model=list[ActionItemRead])
async def list_actions_endpoint(
    status: str | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    building_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("actions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all accessible action items with optional filters."""
    actions = await list_actions(
        db,
        building_id=building_id,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset,
    )
    return actions


@router.get("/buildings/{building_id}/actions", response_model=list[ActionItemRead])
async def list_building_actions_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("actions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all action items for a specific building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    actions = await list_building_actions(db, building_id)
    return actions


@router.post("/buildings/{building_id}/actions", response_model=ActionItemRead, status_code=201)
async def create_action_endpoint(
    building_id: UUID,
    data: ActionItemCreate,
    current_user: User = Depends(require_permission("actions", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual action item for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    action = await create_action(db, building_id, data, created_by=current_user.id)
    await log_action(db, current_user.id, "create", "action_item", action.id)
    return action


@router.put("/actions/{action_id}", response_model=ActionItemRead)
async def update_action_endpoint(
    action_id: UUID,
    data: ActionItemUpdate,
    current_user: User = Depends(require_permission("actions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing action item."""
    action = await update_action(db, action_id, data)
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    await log_action(db, current_user.id, "update", "action_item", action_id)
    return action
