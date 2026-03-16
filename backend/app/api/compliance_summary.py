"""Compliance facade summary API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.compliance_facade import get_compliance_summary

router = APIRouter()


@router.get("/buildings/{building_id}/compliance/summary")
async def get_compliance_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the compliance domain summary for a building."""
    result = await get_compliance_summary(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
