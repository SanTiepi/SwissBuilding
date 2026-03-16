"""
SwissBuildingOS - Notification Digest API

Endpoints for generating and managing notification digests.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification_digest import DigestPreview, NotificationDigest
from app.services.notification_digest_service import (
    generate_digest,
    get_digest_preview,
    mark_digest_sent,
)

router = APIRouter()


@router.get("/notifications/digest", response_model=NotificationDigest)
async def get_digest(
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured notification digest for the current user."""
    return await generate_digest(db, current_user.id, period)


@router.get("/notifications/digest/preview", response_model=DigestPreview)
async def get_preview(
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a lightweight digest preview for the current user."""
    return await get_digest_preview(db, current_user.id, period)


@router.post("/notifications/digest/mark-sent", status_code=200)
async def post_mark_sent(
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark the digest as sent, marking included notifications as read."""
    await mark_digest_sent(db, current_user.id, period)
    return {"status": "ok"}
