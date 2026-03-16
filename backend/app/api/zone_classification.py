"""
SwissBuildingOS - Zone Classification API

4 GET endpoints for zone contamination classification, hierarchy roll-up,
boundary zone identification, and transition history.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.user import User
from app.schemas.zone_classification import (
    BoundaryZoneResult,
    ZoneClassificationResult,
    ZoneHierarchyResult,
    ZoneTransitionHistoryResult,
)
from app.services.zone_classification_service import (
    classify_zones,
    get_zone_hierarchy,
    get_zone_transition_history,
    identify_boundary_zones,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/zone-classification",
    response_model=ZoneClassificationResult,
)
async def classify_zones_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Auto-classify all zones by contamination status."""
    await _get_building_or_404(db, building_id)
    return await classify_zones(db, building_id)


@router.get(
    "/buildings/{building_id}/zone-hierarchy",
    response_model=ZoneHierarchyResult,
)
async def get_zone_hierarchy_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Zone tree with contamination roll-up and floor summaries."""
    await _get_building_or_404(db, building_id)
    return await get_zone_hierarchy(db, building_id)


@router.get(
    "/buildings/{building_id}/boundary-zones",
    response_model=BoundaryZoneResult,
)
async def identify_boundary_zones_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify zones adjacent to contaminated zones needing protective measures."""
    await _get_building_or_404(db, building_id)
    return await identify_boundary_zones(db, building_id)


@router.get(
    "/buildings/{building_id}/zone-transitions",
    response_model=ZoneTransitionHistoryResult,
)
async def get_zone_transition_history_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Status change history per zone over time."""
    await _get_building_or_404(db, building_id)
    return await get_zone_transition_history(db, building_id)
