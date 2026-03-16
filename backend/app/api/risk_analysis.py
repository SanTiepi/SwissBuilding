from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.risk import RenovationSimulationRequest, RenovationSimulationResponse, RiskScoreRead
from app.services.audit_service import log_action
from app.services.renovation_simulator import simulate_renovation

router = APIRouter()


@router.post("/simulate", response_model=RenovationSimulationResponse)
async def simulate_renovation_endpoint(
    data: RenovationSimulationRequest,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Run a renovation simulation to estimate risk reduction and cost."""
    result = await simulate_renovation(db, data.building_id, data.renovation_type)
    await log_action(db, current_user.id, "simulate", "renovation", data.building_id)
    return result


@router.get("/building/{building_id}", response_model=RiskScoreRead)
async def get_risk_scores_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve stored risk score for a building."""
    from sqlalchemy import select

    from app.models.building_risk_score import BuildingRiskScore

    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="No risk scores found for this building")
    return score
