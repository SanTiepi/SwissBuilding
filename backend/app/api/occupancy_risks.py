"""
SwissBuildingOS - Occupancy Risk API

4 GET endpoints for occupancy risk assessment during renovation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.occupancy_risk import (
    OccupancyRiskAssessment,
    OccupantCommunicationPlan,
    PortfolioOccupancyRisk,
    TemporaryRelocationAssessment,
)
from app.services.occupancy_risk_service import (
    assess_occupancy_risk,
    evaluate_temporary_relocation,
    generate_occupant_communication,
    get_portfolio_occupancy_risk,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/occupancy-risk",
    response_model=OccupancyRiskAssessment,
)
async def get_occupancy_risk(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Assess occupancy risk during renovation for a building."""
    try:
        return await assess_occupancy_risk(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/temporary-relocation",
    response_model=TemporaryRelocationAssessment,
)
async def get_temporary_relocation(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate temporary relocation needs for building occupants."""
    try:
        return await evaluate_temporary_relocation(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/occupant-communication",
    response_model=OccupantCommunicationPlan,
)
async def get_occupant_communication(
    building_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate communication plan for building occupants during renovation."""
    try:
        return await generate_occupant_communication(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/organizations/{org_id}/occupancy-risk",
    response_model=PortfolioOccupancyRisk,
)
async def get_org_occupancy_risk(
    org_id: UUID,
    current_user: User = Depends(require_permission("risk_analysis", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level occupancy risk overview for an organization."""
    try:
        return await get_portfolio_occupancy_risk(org_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
