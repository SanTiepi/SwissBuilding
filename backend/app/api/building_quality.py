"""Building data quality endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.quality_service import calculate_building_quality

router = APIRouter()


@router.get("/buildings/{building_id}/quality")
async def get_building_quality(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return quality score for a building."""
    result = await calculate_building_quality(db, building_id)
    if result["overall_score"] == 0.0 and "Building not found" in result.get("missing", []):
        raise HTTPException(status_code=404, detail="Building not found")
    return result
