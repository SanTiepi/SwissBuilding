"""BatiConnect — Obligation Ops API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.obligation import ObligationComplete, ObligationCreate, ObligationRead, ObligationUpdate
from app.services.obligation_service import (
    cancel_obligation,
    complete_obligation,
    create_obligation,
    get_due_soon,
    get_obligation,
    get_overdue,
    list_obligations,
    update_obligation,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_obligation_or_404(db: AsyncSession, obligation_id: UUID):
    obligation = await get_obligation(db, obligation_id)
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return obligation


@router.get(
    "/buildings/{building_id}/obligations",
    response_model=list[ObligationRead],
)
async def list_obligations_endpoint(
    building_id: UUID,
    status: str | None = None,
    obligation_type: str | None = None,
    current_user: User = Depends(require_permission("obligations", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await list_obligations(db, building_id, status_filter=status, obligation_type=obligation_type)


@router.post(
    "/buildings/{building_id}/obligations",
    response_model=ObligationRead,
    status_code=201,
)
async def create_obligation_endpoint(
    building_id: UUID,
    payload: ObligationCreate,
    current_user: User = Depends(require_permission("obligations", "create")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    data.pop("building_id", None)
    obligation = await create_obligation(db, building_id, data)
    await db.commit()
    return obligation


@router.get(
    "/buildings/{building_id}/obligations/due-soon",
    response_model=list[ObligationRead],
)
async def due_soon_endpoint(
    building_id: UUID,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_permission("obligations", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_due_soon(db, building_id, days=days)


@router.get(
    "/buildings/{building_id}/obligations/overdue",
    response_model=list[ObligationRead],
)
async def overdue_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("obligations", "list")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_overdue(db, building_id)


@router.put(
    "/obligations/{obligation_id}",
    response_model=ObligationRead,
)
async def update_obligation_endpoint(
    obligation_id: UUID,
    payload: ObligationUpdate,
    current_user: User = Depends(require_permission("obligations", "update")),
    db: AsyncSession = Depends(get_db),
):
    obligation = await _get_obligation_or_404(db, obligation_id)
    data = payload.model_dump(exclude_unset=True)
    updated = await update_obligation(db, obligation, data)
    await db.commit()
    return updated


@router.post(
    "/obligations/{obligation_id}/complete",
    response_model=ObligationRead,
)
async def complete_obligation_endpoint(
    obligation_id: UUID,
    payload: ObligationComplete | None = None,
    current_user: User = Depends(require_permission("obligations", "update")),
    db: AsyncSession = Depends(get_db),
):
    obligation = await _get_obligation_or_404(db, obligation_id)
    notes = payload.notes if payload else None
    completed, _next = await complete_obligation(db, obligation, current_user.id, notes=notes)
    await db.commit()
    return completed


@router.delete(
    "/obligations/{obligation_id}",
    response_model=ObligationRead,
)
async def delete_obligation_endpoint(
    obligation_id: UUID,
    current_user: User = Depends(require_permission("obligations", "delete")),
    db: AsyncSession = Depends(get_db),
):
    obligation = await _get_obligation_or_404(db, obligation_id)
    cancelled = await cancel_obligation(db, obligation)
    await db.commit()
    return cancelled
