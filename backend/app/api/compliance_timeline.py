"""Compliance timeline endpoints for buildings."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.user import User
from app.schemas.compliance_timeline import (
    ComplianceDeadline,
    ComplianceGapAnalysis,
    ComplianceTimeline,
    PollutantComplianceState,
)
from app.services.compliance_timeline_service import (
    analyze_compliance_gaps,
    build_compliance_timeline,
    get_compliance_deadlines,
    get_next_compliance_actions,
    get_pollutant_compliance_states,
)

router = APIRouter()


async def _verify_building(db: AsyncSession, building_id: uuid.UUID) -> None:
    result = await db.execute(select(Building.id).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Building not found")


@router.get(
    "/buildings/{building_id}/compliance/timeline",
    response_model=ComplianceTimeline,
)
async def get_building_compliance_timeline(
    building_id: uuid.UUID,
    months: int = Query(default=24, ge=1, le=120),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Build chronological compliance timeline for a building."""
    await _verify_building(db, building_id)
    return await build_compliance_timeline(db, building_id, months=months)


@router.get(
    "/buildings/{building_id}/compliance/deadlines",
    response_model=list[ComplianceDeadline],
)
async def get_building_compliance_deadlines(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming and overdue compliance deadlines for a building."""
    await _verify_building(db, building_id)
    return await get_compliance_deadlines(db, building_id)


@router.get(
    "/buildings/{building_id}/compliance/pollutant-states",
    response_model=list[PollutantComplianceState],
)
async def get_building_pollutant_states(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get per-pollutant compliance status for a building."""
    await _verify_building(db, building_id)
    return await get_pollutant_compliance_states(db, building_id)


@router.get(
    "/buildings/{building_id}/compliance/gap-analysis",
    response_model=ComplianceGapAnalysis,
)
async def get_building_gap_analysis(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify compliance gaps for a building."""
    await _verify_building(db, building_id)
    return await analyze_compliance_gaps(db, building_id)


@router.get(
    "/buildings/{building_id}/compliance/next-actions",
    response_model=list[dict],
)
async def get_building_next_actions(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get prioritized next actions needed for full compliance."""
    await _verify_building(db, building_id)
    return await get_next_compliance_actions(db, building_id)
