"""
SwissBuildingOS - Notifications API

User notification management: list, read, preferences, unread count.
All endpoints operate on the current user's own data.
"""

import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.notification import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
)

router = APIRouter()


@router.get("/notifications", response_model=PaginatedResponse[NotificationRead])
async def list_notifications(
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's notifications with optional status filter."""
    base = select(Notification).where(Notification.user_id == current_user.id)

    if status is not None:
        base = base.where(Notification.status == status)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated results, newest first
    offset = (page - 1) * size
    data_stmt = base.order_by(Notification.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(data_stmt)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.put("/notifications/read-all", status_code=200)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for the current user."""
    now = datetime.now(UTC)
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.status == "unread",
        )
        .values(status="read", read_at=now)
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"updated": result.rowcount}


@router.get("/notifications/preferences", response_model=NotificationPreferenceRead)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification preferences for current user. Creates defaults if none exist."""
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == current_user.id))
    pref = result.scalar_one_or_none()

    if pref is None:
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    return pref


@router.put("/notifications/preferences", response_model=NotificationPreferenceRead)
async def update_preferences(
    data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences for current user."""
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == current_user.id))
    pref = result.scalar_one_or_none()

    if pref is None:
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pref, key, value)

    await db.commit()
    await db.refresh(pref)
    return pref


@router.get("/notifications/unread-count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the count of unread notifications for the current user."""
    result = await db.execute(
        select(func.count()).where(
            Notification.user_id == current_user.id,
            Notification.status == "unread",
        )
    )
    count = result.scalar() or 0
    return {"count": count}


@router.put("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read. Only own notifications."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.status = "read"
    notification.read_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(notification)
    return notification
