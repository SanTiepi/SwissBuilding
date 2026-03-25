"""Decision View — API route for unified building decision surface."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.decision_view import DecisionView
from app.services.decision_view_service import get_building_decision_view

router = APIRouter()


@router.get(
    "/buildings/{building_id}/decision-view",
    response_model=DecisionView,
    tags=["Decision View"],
)
async def get_decision_view(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> DecisionView:
    """Get the unified decision-grade view for a building."""
    result = await get_building_decision_view(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
