"""Transaction readiness evaluation API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.transaction_readiness import (
    ComparativeReadiness,
    FinancingScoreBreakdown,
    InsuranceRiskAssessment,
    ReadinessTrend,
    TransactionReadiness,
    TransactionType,
)
from app.services.transaction_readiness_service import (
    compare_transaction_readiness,
    compute_financing_score,
    compute_insurance_risk_tier,
    evaluate_all_transaction_readiness,
    evaluate_transaction_readiness,
    get_readiness_trend,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/transaction-readiness/{transaction_type}",
    response_model=TransactionReadiness,
)
async def get_transaction_readiness_endpoint(
    building_id: UUID,
    transaction_type: TransactionType,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate transaction readiness for a specific transaction type."""
    await _get_building_or_404(db, building_id)
    return await evaluate_transaction_readiness(db, building_id, transaction_type)


@router.get(
    "/buildings/{building_id}/transaction-readiness",
    response_model=list[TransactionReadiness],
)
async def get_all_transaction_readiness_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate transaction readiness for all 4 transaction types."""
    await _get_building_or_404(db, building_id)
    return await evaluate_all_transaction_readiness(db, building_id)


@router.get(
    "/buildings/{building_id}/insurance-risk-tier",
    response_model=InsuranceRiskAssessment,
)
async def get_insurance_risk_tier_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compute insurance premium risk tier for a building."""
    await _get_building_or_404(db, building_id)
    return await compute_insurance_risk_tier(db, building_id)


@router.get(
    "/buildings/{building_id}/financing-score",
    response_model=FinancingScoreBreakdown,
)
async def get_financing_score_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compute detailed financing score breakdown for a building."""
    await _get_building_or_404(db, building_id)
    return await compute_financing_score(db, building_id)


class CompareRequest(BaseModel):
    """Request body for comparative readiness."""

    building_ids: list[UUID] = Field(min_length=2, max_length=10)


@router.post(
    "/transaction-readiness/compare",
    response_model=list[ComparativeReadiness],
)
async def compare_transaction_readiness_endpoint(
    body: CompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare transaction readiness across multiple buildings."""
    try:
        return await compare_transaction_readiness(db, body.building_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/readiness-trend/{transaction_type}",
    response_model=ReadinessTrend,
)
async def get_readiness_trend_endpoint(
    building_id: UUID,
    transaction_type: TransactionType,
    months: int = Query(default=12, ge=1, le=60),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get readiness trend over past N months for a building and transaction type."""
    await _get_building_or_404(db, building_id)
    return await get_readiness_trend(db, building_id, transaction_type, months)
