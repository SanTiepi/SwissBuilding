"""Renovation Sequencer API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.renovation_sequencer import (
    ParallelTracksResult,
    ReadinessBlockersResult,
    RenovationSequence,
    RenovationTimeline,
)
from app.services.renovation_sequencer_service import (
    estimate_renovation_timeline,
    get_renovation_readiness_blockers,
    identify_parallel_tracks,
    plan_renovation_sequence,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/renovation-sequence",
    response_model=RenovationSequence,
)
async def get_renovation_sequence(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return optimal renovation phase ordering for a building."""
    return await plan_renovation_sequence(db, building_id)


@router.get(
    "/buildings/{building_id}/renovation-timeline",
    response_model=RenovationTimeline,
)
async def get_renovation_timeline(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return Gantt-chart-ready renovation timeline."""
    return await estimate_renovation_timeline(db, building_id)


@router.get(
    "/buildings/{building_id}/renovation-parallel-tracks",
    response_model=ParallelTracksResult,
)
async def get_renovation_parallel_tracks(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify works that can run simultaneously."""
    return await identify_parallel_tracks(db, building_id)


@router.get(
    "/buildings/{building_id}/renovation-readiness-blockers",
    response_model=ReadinessBlockersResult,
)
async def get_readiness_blockers(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify blockers preventing renovation start."""
    return await get_renovation_readiness_blockers(db, building_id)
