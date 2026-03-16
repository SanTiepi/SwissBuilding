"""
SwissBuildingOS - Incident Response API

4 GET endpoints for incident response planning.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.incident_response import (
    BuildingIncidentProbability,
    EmergencyContactList,
    IncidentPlan,
    PortfolioIncidentReadiness,
)
from app.services.incident_response_service import (
    assess_incident_probability,
    generate_incident_plan,
    get_emergency_contacts,
    get_portfolio_incident_readiness,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/incident-plan",
    response_model=IncidentPlan,
)
async def get_incident_plan(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Emergency response plan for pollutant incidents in a building."""
    try:
        return await generate_incident_plan(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/emergency-contacts",
    response_model=EmergencyContactList,
)
async def get_building_emergency_contacts(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Structured emergency contact list for incident response."""
    try:
        return await get_emergency_contacts(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/incident-probability",
    response_model=BuildingIncidentProbability,
)
async def get_incident_probability(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Incident probability assessment per zone."""
    try:
        return await assess_incident_probability(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/organizations/{org_id}/incident-readiness",
    response_model=PortfolioIncidentReadiness,
)
async def get_org_incident_readiness(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Organization-level incident readiness overview."""
    try:
        return await get_portfolio_incident_readiness(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
