"""Building snapshot (Time Machine) API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building_snapshot import BuildingSnapshot
from app.models.user import User
from app.schemas.building_snapshot import BuildingSnapshotCreate, BuildingSnapshotRead
from app.schemas.common import PaginatedResponse
from app.services.time_machine_service import capture_snapshot, compare_snapshots, list_snapshots

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/snapshots",
    response_model=BuildingSnapshotRead,
    status_code=201,
)
async def create_snapshot_endpoint(
    building_id: UUID,
    data: BuildingSnapshotCreate,
    current_user: User = Depends(require_permission("building_snapshots", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Capture a new point-in-time snapshot of the building's state."""
    await _get_building_or_404(db, building_id)

    snapshot = await capture_snapshot(
        db,
        building_id=building_id,
        snapshot_type=data.snapshot_type,
        trigger_event=data.trigger_event,
        captured_by=current_user.id,
        notes=data.notes,
    )
    return snapshot


@router.get(
    "/buildings/{building_id}/snapshots",
    response_model=PaginatedResponse[BuildingSnapshotRead],
)
async def list_snapshots_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("building_snapshots", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List snapshots for a building."""
    await _get_building_or_404(db, building_id)

    count_query = select(func.count()).select_from(BuildingSnapshot).where(BuildingSnapshot.building_id == building_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * size
    items = await list_snapshots(db, building_id, limit=size, offset=offset)

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.get(
    "/buildings/{building_id}/snapshots/compare",
)
async def compare_snapshots_endpoint(
    building_id: UUID,
    a: UUID = Query(..., description="First snapshot ID"),
    b: UUID = Query(..., description="Second snapshot ID"),
    current_user: User = Depends(require_permission("building_snapshots", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare two snapshots and return the diff."""
    await _get_building_or_404(db, building_id)

    result = await compare_snapshots(db, building_id, a, b)
    if result is None:
        raise HTTPException(status_code=404, detail="One or both snapshots not found")
    return result


@router.get(
    "/buildings/{building_id}/snapshots/{snapshot_id}",
    response_model=BuildingSnapshotRead,
)
async def get_snapshot_endpoint(
    building_id: UUID,
    snapshot_id: UUID,
    current_user: User = Depends(require_permission("building_snapshots", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single snapshot."""
    await _get_building_or_404(db, building_id)

    result = await db.execute(
        select(BuildingSnapshot).where(
            BuildingSnapshot.id == snapshot_id,
            BuildingSnapshot.building_id == building_id,
        )
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot
