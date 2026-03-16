"""
SwissBuildingOS - Due Diligence API

3 GET + 1 POST endpoints for buyer/investor due diligence on buildings.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.due_diligence import (
    AcquisitionCompareRequest,
    AcquisitionCompareResponse,
    DueDiligenceReport,
    PropertyValueImpact,
    TransactionRiskAssessment,
)
from app.services.due_diligence_service import (
    assess_transaction_risks,
    compare_acquisition_targets,
    estimate_property_value_impact,
    generate_due_diligence_report,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/due-diligence",
    response_model=DueDiligenceReport,
)
async def get_due_diligence_report(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a comprehensive buyer/investor due diligence report."""
    try:
        return await generate_due_diligence_report(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/transaction-risks",
    response_model=TransactionRiskAssessment,
)
async def get_transaction_risks(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Assess categorized transaction risks for a building."""
    try:
        return await assess_transaction_risks(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/value-impact",
    response_model=PropertyValueImpact,
)
async def get_value_impact(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate pollutant-driven property value adjustment."""
    try:
        return await estimate_property_value_impact(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post(
    "/due-diligence/compare",
    response_model=AcquisitionCompareResponse,
)
async def compare_targets(
    data: AcquisitionCompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare acquisition targets side-by-side."""
    try:
        return await compare_acquisition_targets(db, data.building_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
