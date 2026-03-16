"""API routes for regulatory deadline tracking."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.regulatory_deadline import (
    BuildingDeadlines,
    DeadlineCalendar,
    ExpiringCompliance,
    PortfolioDeadlineReport,
)
from app.services.regulatory_deadline_service import (
    check_compliance_expiry,
    get_building_deadlines,
    get_deadline_calendar,
    get_portfolio_deadlines,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/regulatory-deadlines",
    response_model=BuildingDeadlines,
)
async def building_regulatory_deadlines(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingDeadlines:
    """Get all upcoming regulatory deadlines for a building."""
    return await get_building_deadlines(db, building_id)


@router.get(
    "/portfolio/regulatory-deadlines",
    response_model=PortfolioDeadlineReport,
)
async def portfolio_regulatory_deadlines(
    days_ahead: int = Query(default=90, ge=1, le=730),
    org_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PortfolioDeadlineReport:
    """Get aggregate regulatory deadlines across the portfolio."""
    return await get_portfolio_deadlines(db, org_id=org_id, days_ahead=days_ahead)


@router.get(
    "/buildings/{building_id}/deadline-calendar/{year}",
    response_model=DeadlineCalendar,
)
async def building_deadline_calendar(
    building_id: uuid.UUID,
    year: int,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> DeadlineCalendar:
    """Get monthly deadline calendar for a building."""
    return await get_deadline_calendar(db, building_id, year)


@router.get(
    "/buildings/{building_id}/compliance-expiry",
    response_model=list[ExpiringCompliance],
)
async def building_compliance_expiry(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> list[ExpiringCompliance]:
    """Check compliance artefacts nearing expiry."""
    return await check_compliance_expiry(db, building_id)
