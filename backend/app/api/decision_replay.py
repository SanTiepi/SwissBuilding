"""Decision Replay API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.decision_replay import (
    DecisionContext,
    DecisionImpactAnalysis,
    DecisionPattern,
    DecisionRecordCreate,
    DecisionRecordRead,
    DecisionRecordUpdate,
    DecisionTimeline,
)
from app.services.decision_replay_service import (
    get_decision_context,
    get_decision_detail,
    get_decision_impact,
    get_decision_patterns,
    get_decision_timeline,
    record_decision,
    search_decisions,
    update_decision_outcome,
)

router = APIRouter()


@router.post(
    "/buildings/{building_id}/decisions",
    response_model=DecisionRecordRead,
    status_code=201,
)
async def create_decision_endpoint(
    building_id: UUID,
    data: DecisionRecordCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a new decision for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # Override building_id from path
    data = data.model_copy(update={"building_id": building_id})

    record = await record_decision(db, current_user.id, data)
    detail = await get_decision_detail(db, record.id)
    return detail


@router.get(
    "/buildings/{building_id}/decisions",
    response_model=DecisionTimeline,
)
async def list_decisions_endpoint(
    building_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    decision_type: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get chronological decision timeline for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_decision_timeline(db, building_id, limit=limit, decision_type=decision_type)


@router.get(
    "/decisions/search",
    response_model=list[DecisionRecordRead],
)
async def search_decisions_endpoint(
    building_id: UUID | None = Query(None),
    decision_type: str | None = Query(None),
    decided_by: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Search decisions across buildings with filters."""
    return await search_decisions(
        db,
        building_id=building_id,
        decision_type=decision_type,
        decided_by=decided_by,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionRecordRead,
)
async def get_decision_endpoint(
    decision_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single decision detail."""
    detail = await get_decision_detail(db, decision_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Decision not found")
    return detail


@router.put(
    "/decisions/{decision_id}/outcome",
    response_model=DecisionRecordRead,
)
async def update_outcome_endpoint(
    decision_id: UUID,
    data: DecisionRecordUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update the outcome of a decision after it has played out."""
    record = await update_decision_outcome(db, decision_id, data)
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")
    detail = await get_decision_detail(db, record.id)
    return detail


@router.get(
    "/buildings/{building_id}/decisions/patterns",
    response_model=list[DecisionPattern],
)
async def get_patterns_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze decision patterns for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_decision_patterns(db, building_id)


@router.get(
    "/decisions/{decision_id}/context",
    response_model=DecisionContext,
)
async def get_context_endpoint(
    decision_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare building state at decision time vs current state."""
    ctx = await get_decision_context(db, decision_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Decision not found")
    return ctx


@router.get(
    "/buildings/{building_id}/decisions/impact",
    response_model=list[DecisionImpactAnalysis],
)
async def get_impact_endpoint(
    building_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get impact analysis for recent decisions on a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    return await get_decision_impact(db, building_id, limit=limit)
