"""Risk Aggregation API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.risk_aggregation import (
    PortfolioRiskMatrix,
    RiskCorrelationMap,
    RiskDecomposition,
    UnifiedRiskScore,
)
from app.services.risk_aggregation_service import (
    get_portfolio_risk_matrix,
    get_risk_correlation_map,
    get_risk_decomposition,
    get_unified_risk_score,
)

router = APIRouter()


@router.get("/buildings/{building_id}/risk-score", response_model=UnifiedRiskScore)
async def get_building_risk_score(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get unified composite risk score for a building."""
    try:
        return await get_unified_risk_score(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/risk-decomposition", response_model=RiskDecomposition)
async def get_building_risk_decomposition(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get per-dimension risk decomposition with waterfall chart data."""
    try:
        return await get_risk_decomposition(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/buildings/{building_id}/risk-correlations", response_model=RiskCorrelationMap)
async def get_building_risk_correlations(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get risk correlation map showing cascade effects between dimensions."""
    try:
        return await get_risk_correlation_map(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/organizations/{org_id}/risk-matrix", response_model=PortfolioRiskMatrix)
async def get_org_risk_matrix(
    org_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio risk matrix heatmap for an organization."""
    return await get_portfolio_risk_matrix(db, org_id)
