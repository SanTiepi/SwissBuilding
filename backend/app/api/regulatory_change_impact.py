"""Regulatory Change Impact Analyzer API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.regulatory_change_impact import (
    BuildingRegulatorySensitivity,
    ComplianceForecast,
    MultiChangeImpact,
    MultiChangeRequest,
    ThresholdChangeRequest,
    ThresholdChangeSimulation,
)
from app.services.regulatory_change_impact_service import (
    analyze_regulation_impact,
    forecast_compliance_risk,
    get_regulatory_sensitivity,
    simulate_threshold_change,
)

router = APIRouter()


@router.post(
    "/regulatory-impact/simulate-threshold",
    response_model=ThresholdChangeSimulation,
)
async def simulate_threshold(
    body: ThresholdChangeRequest,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate the impact of a single regulatory threshold change."""
    try:
        return await simulate_threshold_change(
            db,
            pollutant=body.pollutant,
            new_threshold=body.new_threshold,
            measurement_type=body.measurement_type,
            org_id=body.org_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/regulatory-impact/analyze-multi-change",
    response_model=MultiChangeImpact,
)
async def analyze_multi_change(
    body: MultiChangeRequest,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Analyze the cumulative impact of multiple regulation changes."""
    try:
        changes = [c.model_dump() for c in body.changes]
        return await analyze_regulation_impact(db, changes, org_id=body.org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/regulatory-sensitivity",
    response_model=BuildingRegulatorySensitivity,
)
async def get_building_sensitivity(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get regulatory sensitivity profile for a building."""
    try:
        return await get_regulatory_sensitivity(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/regulatory-impact/compliance-forecast",
    response_model=ComplianceForecast,
)
async def get_compliance_forecast(
    org_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Forecast compliance risk across the portfolio."""
    return await forecast_compliance_risk(db, org_id=org_id)
