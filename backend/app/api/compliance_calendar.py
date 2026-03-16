"""API routes for compliance calendar."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.compliance_calendar import (
    BuildingCalendar,
    ConflictReport,
    PortfolioCalendar,
    UpcomingDeadlines,
)
from app.services.compliance_calendar_service import (
    detect_scheduling_conflicts,
    get_building_calendar,
    get_portfolio_calendar,
    get_upcoming_deadlines,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/compliance-calendar/{year}",
    response_model=BuildingCalendar,
)
async def building_compliance_calendar(
    building_id: uuid.UUID,
    year: int,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingCalendar:
    """Get monthly compliance calendar for a building."""
    return await get_building_calendar(db, building_id, year)


@router.get(
    "/portfolio/compliance-calendar/{year}",
    response_model=PortfolioCalendar,
)
async def portfolio_compliance_calendar(
    year: int,
    org_id: uuid.UUID | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PortfolioCalendar:
    """Get aggregated compliance calendar across portfolio buildings."""
    return await get_portfolio_calendar(db, org_id, year, month)


@router.get(
    "/buildings/{building_id}/upcoming-deadlines",
    response_model=UpcomingDeadlines,
)
async def building_upcoming_deadlines(
    building_id: uuid.UUID,
    days: int = Query(default=90, ge=1, le=365),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> UpcomingDeadlines:
    """Get upcoming deadlines with auto-generated reminders."""
    return await get_upcoming_deadlines(db, building_id, days)


@router.get(
    "/buildings/{building_id}/scheduling-conflicts",
    response_model=ConflictReport,
)
async def building_scheduling_conflicts(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> ConflictReport:
    """Detect scheduling conflicts for a building."""
    return await detect_scheduling_conflicts(db, building_id)
