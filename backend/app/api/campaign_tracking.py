"""
SwissBuildingOS - Campaign Tracking API

Per-building execution tracking endpoints for campaigns.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.campaign_tracking import (
    BatchStatusUpdate,
    BuildingCampaignStatus,
    BuildingStatusUpdate,
    CampaignExecutionSummary,
    CampaignProgress,
)
from app.services.campaign_tracking_service import (
    batch_update_status,
    get_blocked_buildings,
    get_building_statuses,
    get_campaign_progress,
    get_execution_summary,
    update_building_status,
)

router = APIRouter()


@router.get(
    "/campaigns/{campaign_id}/tracking",
    response_model=list[BuildingCampaignStatus],
)
async def get_tracking_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get per-building tracking statuses for a campaign."""
    return await get_building_statuses(db, campaign_id)


@router.put(
    "/campaigns/{campaign_id}/tracking/{building_id}",
    response_model=BuildingCampaignStatus,
)
async def update_tracking_endpoint(
    campaign_id: UUID,
    building_id: UUID,
    data: BuildingStatusUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a building's tracking status within a campaign."""
    return await update_building_status(db, campaign_id, building_id, data)


@router.get(
    "/campaigns/{campaign_id}/tracking/progress",
    response_model=CampaignProgress,
)
async def get_progress_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated progress metrics for a campaign."""
    return await get_campaign_progress(db, campaign_id)


@router.get(
    "/campaigns/{campaign_id}/tracking/execution-summary",
    response_model=CampaignExecutionSummary,
)
async def get_execution_summary_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get full execution summary with stale detection."""
    return await get_execution_summary(db, campaign_id)


@router.get(
    "/campaigns/{campaign_id}/tracking/blocked",
    response_model=list[BuildingCampaignStatus],
)
async def get_blocked_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get blocked buildings within a campaign."""
    return await get_blocked_buildings(db, campaign_id)


@router.post(
    "/campaigns/{campaign_id}/tracking/batch-update",
)
async def batch_update_endpoint(
    campaign_id: UUID,
    data: BatchStatusUpdate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Batch update multiple buildings to the same status."""
    count = await batch_update_status(db, campaign_id, data.building_ids, data.status)
    return {"updated": count}
