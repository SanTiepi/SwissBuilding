"""Completion Workspace API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.completion_workspace import (
    CompletionStep,
    CompletionWorkspace,
    StepStatusUpdate,
)
from app.services.completion_workspace_service import (
    generate_workspace,
    get_next_steps,
    update_step_status,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/completion-workspace",
    response_model=CompletionWorkspace,
)
async def get_completion_workspace(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return the guided completion workspace for a building."""
    workspace = await generate_workspace(db, building_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return workspace


@router.post(
    "/buildings/{building_id}/completion-workspace/steps/{step_id}/status",
    response_model=CompletionWorkspace,
)
async def update_completion_step_status(
    building_id: UUID,
    step_id: UUID,
    body: StepStatusUpdate,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of a completion step and return the updated workspace."""
    workspace = await generate_workspace(db, building_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Building not found")

    try:
        updated = update_step_status(workspace, step_id, body)
    except ValueError:
        raise HTTPException(status_code=404, detail="Step not found") from None
    return updated


@router.get(
    "/buildings/{building_id}/completion-workspace/next-steps",
    response_model=list[CompletionStep],
)
async def get_next_completion_steps(
    building_id: UUID,
    count: int = Query(default=3, ge=1, le=20),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return the next actionable completion steps for a building."""
    workspace = await generate_workspace(db, building_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return get_next_steps(workspace, count=count)
