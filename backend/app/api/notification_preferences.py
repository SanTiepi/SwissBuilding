"""
SwissBuildingOS - Extended Notification Preferences API

Endpoints for managing channel routing, quiet hours, and per-type notification preferences.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification_preferences import (
    FullNotificationPreferences,
    NotificationPreferencesUpdate,
)
from app.services import notification_preferences_service as svc

router = APIRouter()


@router.get("/notifications/preferences/full", response_model=FullNotificationPreferences)
async def get_full_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get extended notification preferences for the current user."""
    return await svc.get_full_preferences(db, current_user.id)


@router.put("/notifications/preferences/full", response_model=FullNotificationPreferences)
async def update_full_preferences(
    data: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update extended notification preferences with partial data."""
    return await svc.update_preferences(db, current_user.id, data)


@router.get("/notifications/preferences/should-notify")
async def check_should_notify(
    type: str = Query(..., description="Notification type"),
    channel: str = Query("in_app", description="Delivery channel"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a notification should be delivered for the current user."""
    result = await svc.should_notify(db, current_user.id, type, channel)
    return {"should_notify": result}
