"""BatiConnect - Proactive Alerts API routes.

Triggers proactive alert scans and returns alert summaries.
Alerts are created as Notification records visible in NotificationBell.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.proactive_alert import AlertRead, AlertSummaryRead
from app.services.proactive_alert_service import (
    get_alert_summary,
    scan_and_alert,
    scan_portfolio_alerts,
)

router = APIRouter()


@router.post(
    "/buildings/{building_id}/alerts/scan",
    response_model=list[AlertRead],
    tags=["Proactive Alerts"],
)
async def scan_building_alerts(
    building_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a proactive alert scan for a single building."""
    alerts = await scan_and_alert(db, building_id, current_user.id)
    await db.commit()
    return alerts


@router.post(
    "/portfolio/alerts/scan",
    response_model=list[AlertRead],
    tags=["Proactive Alerts"],
)
async def scan_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a proactive alert scan for the entire portfolio."""
    org_id = current_user.organization_id
    if org_id is None:
        raise HTTPException(status_code=400, detail="User has no organization")

    alerts = await scan_portfolio_alerts(db, org_id, current_user.id)
    await db.commit()
    return alerts


@router.get(
    "/portfolio/alerts/summary",
    response_model=AlertSummaryRead,
    tags=["Proactive Alerts"],
)
async def portfolio_alert_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alert summary dashboard data for current user's portfolio."""
    org_id = current_user.organization_id
    if org_id is None:
        return AlertSummaryRead(
            total_alerts=0,
            by_severity={"critical": 0, "warning": 0, "info": 0},
            by_type={},
            buildings_with_alerts=0,
        )

    summary = await get_alert_summary(db, org_id, current_user.id)
    return summary
