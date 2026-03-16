"""Constraint Graph API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.user import User
from app.schemas.constraint_graph import (
    ConstraintGraph,
    CriticalPath,
    ReadinessBlocker,
    SimulateCompletionRequest,
    UnlockAnalysis,
)
from app.services.constraint_graph_service import (
    build_constraint_graph,
    find_critical_path,
    get_next_best_action,
    get_readiness_blockers,
    get_unlock_analysis,
    simulate_completion,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/constraint-graph",
    response_model=ConstraintGraph,
)
async def get_constraint_graph_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return the full constraint graph for a building."""
    await _get_building_or_404(db, building_id)
    return await build_constraint_graph(db, building_id)


@router.get(
    "/buildings/{building_id}/constraint-graph/critical-path",
    response_model=CriticalPath,
)
async def get_critical_path_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return the critical path to full readiness."""
    await _get_building_or_404(db, building_id)
    return await find_critical_path(db, building_id)


@router.get(
    "/buildings/{building_id}/constraint-graph/unlock-analysis",
    response_model=list[UnlockAnalysis],
)
async def get_unlock_analysis_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return unlock analysis sorted by highest leverage."""
    await _get_building_or_404(db, building_id)
    return await get_unlock_analysis(db, building_id)


@router.get(
    "/buildings/{building_id}/constraint-graph/blockers",
    response_model=list[ReadinessBlocker],
)
async def get_blockers_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return readiness blockers with actionable suggestions."""
    await _get_building_or_404(db, building_id)
    return await get_readiness_blockers(db, building_id)


@router.get(
    "/buildings/{building_id}/constraint-graph/next-best-action",
    response_model=UnlockAnalysis | None,
)
async def get_next_best_action_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return the single highest-leverage action to take."""
    await _get_building_or_404(db, building_id)
    return await get_next_best_action(db, building_id)


@router.post(
    "/buildings/{building_id}/constraint-graph/simulate",
    response_model=ConstraintGraph,
)
async def simulate_completion_endpoint(
    building_id: UUID,
    body: SimulateCompletionRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate what the graph looks like if given nodes are completed."""
    await _get_building_or_404(db, building_id)
    return await simulate_completion(db, building_id, body.node_ids)
