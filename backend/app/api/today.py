"""BatiConnect -- Today feed API route."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.today_service import get_today_feed

router = APIRouter()


@router.get("/today")
async def today_feed(
    current_user: User = Depends(require_permission("actions", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Return the daily action feed for the current user's organization."""
    org_id = getattr(current_user, "organization_id", None)
    return await get_today_feed(db, org_id=org_id, user_id=current_user.id)
