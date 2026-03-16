"""Sampling Planner API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.sampling_plan import SamplingPlan
from app.services.sampling_planner import plan_sampling

router = APIRouter()


@router.get(
    "/buildings/{building_id}/sampling-plan",
    response_model=SamplingPlan,
)
async def get_sampling_plan(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a sampling plan with prioritized evidence-collection recommendations."""
    plan = await plan_sampling(db, building_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return plan
