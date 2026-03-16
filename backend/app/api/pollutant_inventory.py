"""Pollutant Inventory API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.pollutant_inventory import (
    BuildingPollutantHotspots,
    BuildingPollutantInventory,
    BuildingPollutantSummary,
    PortfolioPollutantOverview,
)
from app.services.pollutant_inventory_service import (
    get_building_pollutant_inventory,
    get_pollutant_hotspots,
    get_pollutant_summary,
    get_portfolio_pollutant_overview,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/pollutant-inventory",
    response_model=BuildingPollutantInventory,
)
async def building_pollutant_inventory(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingPollutantInventory:
    """Return complete pollutant inventory for a building."""
    return await get_building_pollutant_inventory(db, building_id)


@router.get(
    "/buildings/{building_id}/pollutant-summary",
    response_model=BuildingPollutantSummary,
)
async def building_pollutant_summary(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingPollutantSummary:
    """Return per-pollutant-type summary for a building."""
    return await get_pollutant_summary(db, building_id)


@router.get(
    "/organizations/{org_id}/pollutant-overview",
    response_model=PortfolioPollutantOverview,
)
async def portfolio_pollutant_overview(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PortfolioPollutantOverview:
    """Return pollutant distribution across all buildings of an organization."""
    return await get_portfolio_pollutant_overview(db, org_id)


@router.get(
    "/buildings/{building_id}/pollutant-hotspots",
    response_model=BuildingPollutantHotspots,
)
async def building_pollutant_hotspots(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingPollutantHotspots:
    """Return pollutant hotspot zones for a building, ranked by risk."""
    return await get_pollutant_hotspots(db, building_id)
