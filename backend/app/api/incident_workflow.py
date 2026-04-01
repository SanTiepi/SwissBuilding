"""Incident Workflow API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.incident_workflow_service import (
    create_incident,
    escalate_incident,
    get_incident_patterns,
    resolve_incident,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas (inline to avoid hub-file edits)
# ---------------------------------------------------------------------------


class IncidentCreateRequest(BaseModel):
    incident_type: str
    title: str
    description: str | None = None
    severity: str = "minor"
    location_description: str | None = None
    zone_id: uuid.UUID | None = None
    element_id: uuid.UUID | None = None
    cause_category: str = "unknown"
    occupant_impact: bool = False
    service_disruption: bool = False


class IncidentEscalateRequest(BaseModel):
    new_severity: str


class IncidentResolveRequest(BaseModel):
    response_description: str | None = None
    repair_cost_chf: float | None = None
    intervention_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/incidents/{building_id}", status_code=201)
async def create_incident_endpoint(
    building_id: uuid.UUID,
    data: IncidentCreateRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new incident for a building."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    org_id = building.organization_id or current_user.organization_id
    if org_id is None:
        raise HTTPException(status_code=400, detail="Building or user must belong to an organization")

    incident = await create_incident(
        db,
        building_id=building_id,
        organization_id=org_id,
        data=data.model_dump(),
        created_by_id=current_user.id,
    )
    return {
        "id": str(incident.id),
        "building_id": str(incident.building_id),
        "incident_type": incident.incident_type,
        "title": incident.title,
        "severity": incident.severity,
        "status": incident.status,
        "recurring": incident.recurring,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


@router.put("/incidents/{incident_id}/escalate")
async def escalate_incident_endpoint(
    incident_id: uuid.UUID,
    data: IncidentEscalateRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Escalate an incident's severity."""
    try:
        incident = await escalate_incident(db, incident_id, data.new_severity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return {
        "id": str(incident.id),
        "severity": incident.severity,
        "status": incident.status,
        "title": incident.title,
    }


@router.put("/incidents/{incident_id}/resolve")
async def resolve_incident_endpoint(
    incident_id: uuid.UUID,
    data: IncidentResolveRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an incident."""
    try:
        incident = await resolve_incident(db, incident_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return {
        "id": str(incident.id),
        "status": incident.status,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "repair_cost_chf": incident.repair_cost_chf,
    }


@router.get("/incidents/{building_id}/patterns")
async def get_patterns_endpoint(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get recurring incident patterns for a building."""
    return await get_incident_patterns(db, building_id)
