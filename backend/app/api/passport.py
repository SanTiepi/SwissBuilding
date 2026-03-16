"""Building passport summary API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.passport_service import get_passport_summary

router = APIRouter()


@router.get("/buildings/{building_id}/passport/summary")
async def get_passport_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the building passport summary state."""
    result = await get_passport_summary(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
