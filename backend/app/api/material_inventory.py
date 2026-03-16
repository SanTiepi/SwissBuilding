"""Material Inventory API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.material_inventory import (
    BuildingMaterialInventory,
    BuildingMaterialLifecycle,
    BuildingMaterialRisk,
    PortfolioMaterialOverview,
)
from app.services.material_inventory_service import (
    assess_material_risk,
    get_material_inventory,
    get_material_lifecycle,
    get_portfolio_material_overview,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/material-inventory",
    response_model=BuildingMaterialInventory,
)
async def building_material_inventory(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingMaterialInventory:
    """Return complete material inventory for a building, grouped by type."""
    return await get_material_inventory(db, building_id)


@router.get(
    "/buildings/{building_id}/material-risk",
    response_model=BuildingMaterialRisk,
)
async def building_material_risk(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingMaterialRisk:
    """Return risk assessment for all materials in a building."""
    return await assess_material_risk(db, building_id)


@router.get(
    "/buildings/{building_id}/material-lifecycle",
    response_model=BuildingMaterialLifecycle,
)
async def building_material_lifecycle(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingMaterialLifecycle:
    """Return lifecycle analysis for all materials in a building."""
    return await get_material_lifecycle(db, building_id)


@router.get(
    "/organizations/{org_id}/material-overview",
    response_model=PortfolioMaterialOverview,
)
async def portfolio_material_overview(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PortfolioMaterialOverview:
    """Return material overview across all buildings of an organization."""
    return await get_portfolio_material_overview(db, org_id)
