"""RénoPredict — Remediation cost estimation API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cost_prediction import CostPredictionRequest, CostPredictionResponse
from app.services.cost_predictor_service import CostPredictionError, predict_cost

router = APIRouter()


@router.post(
    "/predict/cost",
    response_model=CostPredictionResponse,
    summary="Estimate remediation cost for a pollutant",
    description=(
        "Compute a fourchette (min/median/max) for pollutant remediation "
        "based on Swiss market averages, canton coefficients, and accessibility."
    ),
)
async def predict_cost_endpoint(
    request: CostPredictionRequest,
    current_user: User = Depends(require_permission("simulations", "read")),
    db: AsyncSession = Depends(get_db),
) -> CostPredictionResponse:
    try:
        return await predict_cost(db, request)
    except CostPredictionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
