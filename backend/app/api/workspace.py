"""BatiConnect — Workspace membership API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.models.workspace_membership import WORKSPACE_ROLES
from app.schemas.workspace import WorkspaceMembershipCreate, WorkspaceMembershipRead, WorkspaceMembershipUpdate
from app.services.workspace_service import (
    add_member,
    enrich_membership,
    enrich_memberships,
    get_member,
    get_members,
    remove_member,
    update_member_scope,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/workspace/members",
    response_model=list[WorkspaceMembershipRead],
)
async def list_workspace_members(
    building_id: UUID,
    active_only: bool = True,
    current_user: User = Depends(require_permission("assignments", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    memberships = await get_members(db, building_id, active_only=active_only)
    enriched = await enrich_memberships(db, memberships)
    return enriched


@router.post(
    "/buildings/{building_id}/workspace/members",
    response_model=WorkspaceMembershipRead,
    status_code=201,
)
async def create_workspace_member(
    building_id: UUID,
    payload: WorkspaceMembershipCreate,
    current_user: User = Depends(require_permission("assignments", "create")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)

    if payload.role not in WORKSPACE_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {payload.role}")

    data = payload.model_dump(exclude_unset=True)
    membership = await add_member(db, building_id, data, granted_by=current_user.id)
    await db.commit()
    return await enrich_membership(db, membership)


@router.put(
    "/workspace/members/{membership_id}",
    response_model=WorkspaceMembershipRead,
)
async def update_workspace_member(
    membership_id: UUID,
    payload: WorkspaceMembershipUpdate,
    current_user: User = Depends(require_permission("assignments", "create")),
    db: AsyncSession = Depends(get_db),
):
    existing = await get_member(db, membership_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Membership not found")

    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in WORKSPACE_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {data['role']}")

    updated = await update_member_scope(db, membership_id, data)
    await db.commit()
    return await enrich_membership(db, updated)


@router.delete(
    "/workspace/members/{membership_id}",
    response_model=WorkspaceMembershipRead,
)
async def delete_workspace_member(
    membership_id: UUID,
    current_user: User = Depends(require_permission("assignments", "delete")),
    db: AsyncSession = Depends(get_db),
):
    membership = await remove_member(db, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    await db.commit()
    return await enrich_membership(db, membership)
