"""Building comparison API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_comparison import (
    BuildingComparison,
    BuildingComparisonRequest,
)
from app.services.building_comparison_service import compare_buildings

router = APIRouter()


@router.post("/buildings/compare", response_model=BuildingComparison)
async def compare_buildings_endpoint(
    body: BuildingComparisonRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare 2-10 buildings side by side on passport, trust, readiness, and completeness."""
    try:
        result = await compare_buildings(db, body.building_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result
