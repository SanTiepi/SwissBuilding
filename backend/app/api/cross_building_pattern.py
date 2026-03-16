"""Cross-building pattern detection API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cross_building_pattern import (
    GeographicClusterResult,
    PatternDetectionResult,
    SimilarBuildingsResult,
    UndiscoveredPollutantResult,
)
from app.services.cross_building_pattern_service import (
    detect_patterns,
    find_similar_buildings,
    get_geographic_clusters,
    predict_undiscovered_pollutants,
)

router = APIRouter()


@router.get(
    "/organizations/{org_id}/cross-building-patterns",
    response_model=PatternDetectionResult,
)
async def get_cross_building_patterns(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect systemic, contractor-quality, and geographic patterns across buildings."""
    return await detect_patterns(db, org_id)


@router.get(
    "/buildings/{building_id}/similar",
    response_model=SimilarBuildingsResult,
)
async def get_similar_buildings(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Find buildings with similar characteristics."""
    try:
        return await find_similar_buildings(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/geographic-clusters",
    response_model=GeographicClusterResult,
)
async def get_geographic_clusters_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get spatial clusters of risk across buildings."""
    return await get_geographic_clusters(db, org_id)


@router.get(
    "/buildings/{building_id}/undiscovered-pollutants",
    response_model=UndiscoveredPollutantResult,
)
async def get_undiscovered_pollutants(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Predict untested pollutants based on peer analysis."""
    try:
        return await predict_undiscovered_pollutants(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
