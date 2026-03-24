"""SwissBuildingOS — Material Recommendations API route."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.material_recommendation import MaterialRecommendationReport
from app.services.material_recommendation_service import generate_recommendations

router = APIRouter()


@router.get(
    "/buildings/{building_id}/material-recommendations",
    response_model=MaterialRecommendationReport,
)
async def get_material_recommendations(
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("buildings", "read")),
) -> MaterialRecommendationReport:
    """Get material replacement recommendations for a building."""
    try:
        return await generate_recommendations(db, building_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
