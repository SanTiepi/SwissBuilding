"""Waste management API routes (OLED-compliant)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.waste_management import (
    BuildingWasteClassification,
    BuildingWasteVolumes,
    PortfolioWasteForecast,
    WastePlan,
)
from app.services.waste_management_service import (
    classify_building_waste,
    estimate_waste_volumes,
    generate_waste_plan,
    get_portfolio_waste_forecast,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/waste-classification",
    response_model=BuildingWasteClassification,
)
async def get_waste_classification(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Classify building waste per sample according to OLED regulations."""
    try:
        return await classify_building_waste(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/waste-plan",
    response_model=WastePlan,
)
async def get_waste_plan(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate OLED-compliant waste management plan for a building."""
    try:
        return await generate_waste_plan(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/waste-volumes",
    response_model=BuildingWasteVolumes,
)
async def get_waste_volumes(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate waste volumes per category for a building."""
    try:
        return await estimate_waste_volumes(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/waste-forecast",
    response_model=PortfolioWasteForecast,
)
async def get_waste_forecast(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated waste forecast for an organization's portfolio."""
    try:
        return await get_portfolio_waste_forecast(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
