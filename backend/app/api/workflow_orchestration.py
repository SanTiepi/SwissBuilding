"""Workflow Orchestration API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.workflow_orchestration import (
    BuildingWorkflows,
    WorkflowAdvance,
    WorkflowCreate,
    WorkflowInstance,
    WorkflowStatus,
)
from app.services.workflow_orchestration_service import (
    advance_workflow,
    create_workflow,
    get_building_workflows,
    get_workflow_status,
)

router = APIRouter()


@router.post(
    "/buildings/{building_id}/workflows",
    response_model=WorkflowInstance,
    status_code=201,
)
async def create_building_workflow(
    building_id: uuid.UUID,
    body: WorkflowCreate,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow for a building."""
    if body.building_id != building_id:
        raise HTTPException(status_code=400, detail="building_id mismatch")
    try:
        result = await create_workflow(db, building_id, body.workflow_type, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return result


@router.post(
    "/workflows/{workflow_id}/advance",
    response_model=WorkflowInstance,
)
async def advance_building_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowAdvance,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Advance a workflow to the next step."""
    try:
        result = await advance_workflow(db, workflow_id, body.action, current_user.id, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return result


@router.get(
    "/workflows/{workflow_id}/status",
    response_model=WorkflowStatus,
)
async def get_workflow_status_endpoint(
    workflow_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get full status of a workflow."""
    try:
        result = await get_workflow_status(db, workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return result


@router.get(
    "/buildings/{building_id}/workflows",
    response_model=BuildingWorkflows,
)
async def get_building_workflows_endpoint(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all workflows for a building."""
    try:
        result = await get_building_workflows(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return result
