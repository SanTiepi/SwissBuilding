"""Ventilation Assessment API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.ventilation_assessment import (
    AirQualityMonitoringPlan,
    PortfolioVentilationStatus,
    RadonVentilationEvaluation,
    VentilationAssessment,
)
from app.services.ventilation_assessment_service import (
    assess_ventilation_needs,
    evaluate_radon_ventilation,
    get_air_quality_monitoring_plan,
    get_portfolio_ventilation_status,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/ventilation-assessment",
    response_model=VentilationAssessment,
)
async def get_building_ventilation_assessment(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Per-zone ventilation requirements based on pollutants found."""
    return await assess_ventilation_needs(db, building_id)


@router.get(
    "/buildings/{building_id}/radon-ventilation",
    response_model=RadonVentilationEvaluation,
)
async def get_building_radon_ventilation(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Radon-specific ventilation adequacy and mitigation recommendations."""
    return await evaluate_radon_ventilation(db, building_id)


@router.get(
    "/buildings/{building_id}/air-quality-monitoring",
    response_model=AirQualityMonitoringPlan,
)
async def get_building_air_quality_monitoring(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Air quality monitoring plan during and after remediation."""
    return await get_air_quality_monitoring_plan(db, building_id)


@router.get(
    "/organizations/{org_id}/ventilation-status",
    response_model=PortfolioVentilationStatus,
)
async def get_org_ventilation_status(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Org-level ventilation status: upgrades needed, radon priority, ORaP compliance."""
    return await get_portfolio_ventilation_status(db, org_id)
