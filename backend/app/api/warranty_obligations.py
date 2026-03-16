"""API endpoints for warranty obligations tracking."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.warranty_obligations import (
    BuildingDefectSummary,
    BuildingObligationsSchedule,
    BuildingWarrantyReport,
    PortfolioWarrantyOverview,
)
from app.services.warranty_obligations_service import (
    get_building_warranty_report,
    get_defect_summary,
    get_obligations_schedule,
    get_portfolio_warranty_overview,
)

router = APIRouter()


@router.get(
    "/warranty-obligations/buildings/{building_id}/warranties",
    response_model=BuildingWarrantyReport,
)
async def get_warranties(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await get_building_warranty_report(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/warranty-obligations/buildings/{building_id}/obligations",
    response_model=BuildingObligationsSchedule,
)
async def get_obligations(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await get_obligations_schedule(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/warranty-obligations/buildings/{building_id}/defects",
    response_model=BuildingDefectSummary,
)
async def get_defects(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await get_defect_summary(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/warranty-obligations/organizations/{org_id}/overview",
    response_model=PortfolioWarrantyOverview,
)
async def get_overview(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await get_portfolio_warranty_overview(org_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
