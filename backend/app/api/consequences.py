"""API routes for the consequence engine."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.consequence_engine import ConsequenceEngine, get_last_consequence_run

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/consequences/run",
    tags=["Consequences"],
    status_code=200,
)
async def run_consequences_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the consequence chain for a building."""
    await _get_building_or_404(db, building_id)
    engine = ConsequenceEngine()
    result = await engine.run_consequences(
        db,
        building_id,
        trigger_type="manual_update",
        triggered_by_id=current_user.id,
    )
    await db.commit()
    return result


@router.get(
    "/buildings/{building_id}/consequences/last",
    tags=["Consequences"],
)
async def get_last_consequence_run_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the last consequence run result for a building."""
    await _get_building_or_404(db, building_id)
    run = await get_last_consequence_run(db, building_id)
    if run is None:
        return {"message": "No consequence run found for this building"}
    return {
        "id": str(run.id),
        "building_id": str(run.building_id),
        "trigger_type": run.trigger_type,
        "trigger_id": run.trigger_id,
        "status": run.status,
        "result": run.result_json,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
