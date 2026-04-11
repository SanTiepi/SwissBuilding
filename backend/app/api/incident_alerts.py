"""BatiConnect - Incident Prediction Alerts API (Programme S)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.incident_prediction_service import (
    get_building_forecast_stub,
    predict_incidents,
)
from app.services.meteo_incident_correlation_service import analyze_correlations

router = APIRouter()


@router.get("/buildings/{building_id}/incident-correlations")
async def get_incident_correlations(
    building_id: UUID,
    lookback_years: int = 2,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get meteo/incident correlation analysis for a building."""
    try:
        result = await analyze_correlations(db, building_id, lookback_years=lookback_years)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.get("/buildings/{building_id}/incident-predictions")
async def get_incident_predictions(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get predicted incidents based on weather forecast + historical correlations."""
    try:
        forecast = await get_building_forecast_stub(db, building_id)
        result = await predict_incidents(db, building_id, forecast=forecast)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result
