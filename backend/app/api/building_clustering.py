"""Building clustering API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_clustering import (
    ClusterSummary,
    EraClusterResult,
    OutlierBuildingResult,
    RiskProfileClusterResult,
)
from app.services.building_clustering_service import (
    cluster_by_construction_era,
    cluster_by_risk_profile,
    find_outlier_buildings,
    get_cluster_summary,
)

router = APIRouter()


@router.get(
    "/organizations/{org_id}/building-clusters/risk-profile",
    response_model=RiskProfileClusterResult,
)
async def get_risk_profile_clusters(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Group buildings by similar risk profiles (pollutant patterns)."""
    return await cluster_by_risk_profile(db, org_id)


@router.get(
    "/organizations/{org_id}/building-clusters/construction-era",
    response_model=EraClusterResult,
)
async def get_construction_era_clusters(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Group buildings by construction period with era-specific insights."""
    return await cluster_by_construction_era(db, org_id)


@router.get(
    "/organizations/{org_id}/building-clusters/outliers",
    response_model=OutlierBuildingResult,
)
async def get_outlier_buildings(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Find buildings that deviate from their cluster norms."""
    return await find_outlier_buildings(db, org_id)


@router.get(
    "/organizations/{org_id}/building-clusters/summary",
    response_model=ClusterSummary,
)
async def get_cluster_summary_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """High-level clustering overview for the organization."""
    return await get_cluster_summary(db, org_id)
