"""Building Lifecycle API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_lifecycle import (
    LifecyclePhaseResponse,
    LifecyclePredictionResponse,
    LifecycleTimelineResponse,
    PortfolioLifecycleDistributionResponse,
)
from app.services.building_lifecycle_service import (
    get_lifecycle_phase,
    get_lifecycle_timeline,
    get_portfolio_lifecycle_distribution,
    predict_next_phase,
)

router = APIRouter()


@router.get("/buildings/{building_id}/lifecycle-phase", response_model=LifecyclePhaseResponse)
async def api_get_lifecycle_phase(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the current lifecycle phase for a building."""
    result = await get_lifecycle_phase(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/buildings/{building_id}/lifecycle-timeline", response_model=LifecycleTimelineResponse)
async def api_get_lifecycle_timeline(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the full lifecycle timeline for a building."""
    result = await get_lifecycle_timeline(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/buildings/{building_id}/lifecycle-prediction", response_model=LifecyclePredictionResponse)
async def api_get_lifecycle_prediction(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Predict the next lifecycle phase for a building."""
    result = await predict_next_phase(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/lifecycle-distribution",
    response_model=PortfolioLifecycleDistributionResponse,
)
async def api_get_portfolio_lifecycle_distribution(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get lifecycle distribution across buildings for an organization."""
    result = await get_portfolio_lifecycle_distribution(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
