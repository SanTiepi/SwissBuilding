"""Building completeness evaluation endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.completeness import CompletenessResult
from app.services.completeness_engine import evaluate_completeness

router = APIRouter()


@router.get(
    "/buildings/{building_id}/completeness",
    response_model=CompletenessResult,
)
async def get_building_completeness(
    building_id: uuid.UUID,
    stage: str = Query(default="avt", pattern="^(avt|apt)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate completeness of a building dossier for a workflow stage."""
    result = await evaluate_completeness(db, building_id, workflow_stage=stage)
    if result.overall_score == 0.0 and "Building not found" in result.missing_items:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
