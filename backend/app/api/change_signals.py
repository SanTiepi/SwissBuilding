# COMPATIBILITY SURFACE — ChangeSignal is frozen per ADR-004.
# Canonical change objects are in building_change.py (BuildingSignal).
# No new semantics should be added here.
# RETIREMENT PLANNED: Sunset 2026-09-30, successor = /api/v1/truth/buildings/{id}/changes

"""Change signal management API routes (DEPRECATED — use building_changes API)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.change_signal import ChangeSignal
from app.models.user import User
from app.schemas.change_signal import (
    ChangeSignalCreate,
    ChangeSignalRead,
    ChangeSignalUpdate,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


async def _deprecation_headers(response: Response) -> None:
    """Inject deprecation headers on all change_signals endpoints (RFC 8594)."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-09-30"
    response.headers["Link"] = '</api/v1/buildings/{id}/signals>; rel="successor-version"'


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_signal_or_404(db: AsyncSession, building_id: UUID, signal_id: UUID) -> ChangeSignal:
    result = await db.execute(
        select(ChangeSignal).where(
            ChangeSignal.id == signal_id,
            ChangeSignal.building_id == building_id,
        )
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Change signal not found")
    return signal


@router.get(
    "/portfolio/change-signals",
    response_model=PaginatedResponse[ChangeSignalRead],
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
async def list_portfolio_change_signals(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    signal_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("change_signals", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List change signals across all buildings (portfolio view)."""
    query = select(ChangeSignal)
    count_query = select(func.count()).select_from(ChangeSignal)

    if signal_type:
        query = query.where(ChangeSignal.signal_type == signal_type)
        count_query = count_query.where(ChangeSignal.signal_type == signal_type)
    if severity:
        query = query.where(ChangeSignal.severity == severity)
        count_query = count_query.where(ChangeSignal.severity == severity)
    if status:
        query = query.where(ChangeSignal.status == status)
        count_query = count_query.where(ChangeSignal.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ChangeSignal.detected_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.get(
    "/buildings/{building_id}/change-signals",
    response_model=PaginatedResponse[ChangeSignalRead],
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
async def list_change_signals_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    signal_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("change_signals", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List change signals for a building."""
    await _get_building_or_404(db, building_id)

    query = select(ChangeSignal).where(ChangeSignal.building_id == building_id)
    count_query = select(func.count()).select_from(ChangeSignal).where(ChangeSignal.building_id == building_id)

    if signal_type:
        query = query.where(ChangeSignal.signal_type == signal_type)
        count_query = count_query.where(ChangeSignal.signal_type == signal_type)
    if severity:
        query = query.where(ChangeSignal.severity == severity)
        count_query = count_query.where(ChangeSignal.severity == severity)
    if status:
        query = query.where(ChangeSignal.status == status)
        count_query = count_query.where(ChangeSignal.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ChangeSignal.detected_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post(
    "/buildings/{building_id}/change-signals",
    response_model=ChangeSignalRead,
    status_code=201,
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
async def create_change_signal_endpoint(
    building_id: UUID,
    data: ChangeSignalCreate,
    current_user: User = Depends(require_permission("change_signals", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new change signal."""
    await _get_building_or_404(db, building_id)

    signal = ChangeSignal(
        building_id=building_id,
        **data.model_dump(),
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)
    return signal


@router.get(
    "/buildings/{building_id}/change-signals/{signal_id}",
    response_model=ChangeSignalRead,
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
async def get_change_signal_endpoint(
    building_id: UUID,
    signal_id: UUID,
    current_user: User = Depends(require_permission("change_signals", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single change signal."""
    await _get_building_or_404(db, building_id)
    return await _get_signal_or_404(db, building_id, signal_id)


@router.put(
    "/buildings/{building_id}/change-signals/{signal_id}",
    response_model=ChangeSignalRead,
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
async def update_change_signal_endpoint(
    building_id: UUID,
    signal_id: UUID,
    data: ChangeSignalUpdate,
    current_user: User = Depends(require_permission("change_signals", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a change signal."""
    await _get_building_or_404(db, building_id)
    signal = await _get_signal_or_404(db, building_id, signal_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(signal, key, value)

    await db.commit()
    await db.refresh(signal)
    return signal


@router.delete(
    "/buildings/{building_id}/change-signals/{signal_id}",
    status_code=204,
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
async def delete_change_signal_endpoint(
    building_id: UUID,
    signal_id: UUID,
    current_user: User = Depends(require_permission("change_signals", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a change signal."""
    await _get_building_or_404(db, building_id)
    signal = await _get_signal_or_404(db, building_id, signal_id)
    await db.delete(signal)
    await db.commit()
