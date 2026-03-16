"""API endpoints for the notification rules engine."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification_rules import (
    BuildingTriggersResponse,
    DigestResponse,
    NotificationPreferencesResponse,
    OrgAlertSummary,
)
from app.services.notification_rules_service import (
    evaluate_building_triggers,
    generate_digest,
    get_notification_preferences,
    get_org_alert_summary,
)

router = APIRouter()


@router.get("/triggers/{building_id}", response_model=BuildingTriggersResponse)
async def get_building_triggers(
    building_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate notification triggers for a specific building."""
    return await evaluate_building_triggers(building_id, db)


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's notification rule preferences."""
    return await get_notification_preferences(current_user.id, db)


@router.get("/digest", response_model=DigestResponse)
async def get_digest(
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a notification rules digest for the current user."""
    return await generate_digest(current_user.id, db, period)


@router.get("/org-summary/{org_id}", response_model=OrgAlertSummary)
async def get_org_summary(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get an organization-wide alert summary."""
    return await get_org_alert_summary(org_id, db)
