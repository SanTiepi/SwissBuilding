"""Recommendation Engine API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.recommendation import RecommendationListRead, RecommendationRead
from app.services.recommendation_engine import generate_recommendations

router = APIRouter()


@router.get(
    "/buildings/{building_id}/recommendations",
    response_model=RecommendationListRead,
)
async def get_recommendations(
    building_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get prioritized recommendations for a building."""
    recs = await generate_recommendations(db, building_id, limit=limit)
    return RecommendationListRead(
        building_id=building_id,
        recommendations=[RecommendationRead(**r) for r in recs],
        total=len(recs),
    )
