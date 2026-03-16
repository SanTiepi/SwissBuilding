"""Risk Mitigation Planner API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.risk_mitigation import (
    DependencyAnalysis,
    MitigationPlan,
    PlanTimeline,
    QuickWin,
)
from app.services.risk_mitigation_planner import (
    analyze_intervention_dependencies,
    estimate_plan_timeline,
    generate_mitigation_plan,
    get_quick_wins,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/mitigation-plan",
    response_model=MitigationPlan,
)
async def get_mitigation_plan(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an optimal remediation sequence for a building."""
    try:
        return await generate_mitigation_plan(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/quick-wins",
    response_model=list[QuickWin],
)
async def get_building_quick_wins(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify low-cost, high-impact remediation actions."""
    try:
        return await get_quick_wins(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/intervention-dependencies",
    response_model=DependencyAnalysis,
)
async def get_intervention_dependencies(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze intervention dependencies and critical path."""
    try:
        return await analyze_intervention_dependencies(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/plan-timeline",
    response_model=PlanTimeline,
)
async def get_plan_timeline(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a week-by-week timeline with milestones and cost curve."""
    try:
        return await estimate_plan_timeline(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
