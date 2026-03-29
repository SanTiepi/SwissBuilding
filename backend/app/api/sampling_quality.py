"""Sampling Quality Score API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.sampling_quality import (
    BuildingSamplingQualityRead,
    SamplingQualityRead,
)
from app.services.sampling_quality_service import (
    evaluate_building_sampling_quality,
    evaluate_sampling_quality,
)

router = APIRouter()


@router.get(
    "/diagnostics/{diagnostic_id}/sampling-quality",
    response_model=SamplingQualityRead,
)
async def get_diagnostic_sampling_quality(
    diagnostic_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate sampling protocol quality for a diagnostic."""
    result = await evaluate_sampling_quality(db, diagnostic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    return result


@router.get(
    "/buildings/{building_id}/sampling-quality",
    response_model=BuildingSamplingQualityRead,
)
async def get_building_sampling_quality(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate aggregate sampling quality for all diagnostics of a building."""
    result = await evaluate_building_sampling_quality(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
