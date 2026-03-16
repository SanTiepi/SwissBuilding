"""
SwissBuildingOS - Spatial Risk Mapping API

4 GET endpoints for spatial risk mapping of buildings.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.spatial_risk_mapping import (
    BuildingRiskMap,
    FloorRiskProfile,
    RiskPropagationAnalysis,
    SpatialCoverageGaps,
)
from app.services.spatial_risk_mapping_service import (
    get_building_risk_map,
    get_floor_risk_profile,
    get_risk_propagation_analysis,
    get_spatial_coverage_gaps,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/risk-map",
    response_model=BuildingRiskMap,
)
async def building_risk_map(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Zone-by-zone risk overlay for a building."""
    try:
        return await get_building_risk_map(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/floor-risk/{floor}",
    response_model=FloorRiskProfile,
)
async def floor_risk_profile(
    building_id: UUID,
    floor: int,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Single floor risk profile with pollutant distribution."""
    try:
        return await get_floor_risk_profile(db, building_id, floor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/risk-propagation",
    response_model=RiskPropagationAnalysis,
)
async def risk_propagation(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Adjacent zone contamination risk propagation analysis."""
    try:
        return await get_risk_propagation_analysis(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/coverage-gaps",
    response_model=SpatialCoverageGaps,
)
async def coverage_gaps(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Spatial coverage gaps: zones without samples, floors without diagnostics."""
    try:
        return await get_spatial_coverage_gaps(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
