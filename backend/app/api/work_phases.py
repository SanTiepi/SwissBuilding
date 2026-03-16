"""Work Phases API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.work_phase import (
    PhaseRequirements,
    PhaseTimeline,
    PortfolioWorkOverview,
    WorkPhasePlan,
)
from app.services.work_phase_service import (
    estimate_phase_timeline,
    get_phase_requirements,
    get_portfolio_work_overview,
    plan_work_phases,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/work-phases",
    response_model=WorkPhasePlan,
)
async def get_work_phases(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return ordered work phases for a building renovation."""
    return await plan_work_phases(db, building_id)


@router.get(
    "/buildings/{building_id}/work-phases/timeline",
    response_model=PhaseTimeline,
)
async def get_work_phase_timeline(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return Gantt-style timeline for work phases."""
    return await estimate_phase_timeline(db, building_id)


@router.get(
    "/buildings/{building_id}/work-phases/{phase_type}/requirements",
    response_model=PhaseRequirements,
)
async def get_work_phase_requirements(
    building_id: uuid.UUID,
    phase_type: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return detailed requirements for a specific work phase type."""
    return await get_phase_requirements(db, building_id, phase_type)


@router.get(
    "/organizations/{organization_id}/work-overview",
    response_model=PortfolioWorkOverview,
)
async def get_org_work_overview(
    organization_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return organization-wide work phase overview."""
    return await get_portfolio_work_overview(db, organization_id)
