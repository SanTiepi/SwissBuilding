"""API routes for the review queue."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.review_queue import (
    ReviewQueueStats,
    ReviewTaskAssign,
    ReviewTaskComplete,
    ReviewTaskEscalate,
    ReviewTaskRead,
)
from app.services import review_queue_service

router = APIRouter()


@router.get(
    "/review-queue",
    response_model=list[ReviewTaskRead],
    tags=["Review Queue"],
)
async def get_review_queue(
    status: str | None = Query("pending", description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    task_type: str | None = Query(None, description="Filter by task type"),
    building_id: UUID | None = Query(None, description="Filter by building"),
    assigned_to_id: UUID | None = Query(None, description="Filter by assignee"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the review queue with filters. Sorted by priority then created_at."""
    tasks = await review_queue_service.get_queue(
        db,
        organization_id=current_user.organization_id,
        status=status,
        priority=priority,
        task_type=task_type,
        building_id=building_id,
        assigned_to_id=assigned_to_id,
        limit=limit,
        offset=offset,
    )
    return tasks


@router.get(
    "/review-queue/stats",
    response_model=ReviewQueueStats,
    tags=["Review Queue"],
)
async def get_review_queue_stats(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get review queue statistics."""
    stats = await review_queue_service.get_queue_stats(db, current_user.organization_id)
    return stats


@router.post(
    "/review-tasks/{task_id}/assign",
    response_model=ReviewTaskRead,
    tags=["Review Queue"],
)
async def assign_review_task(
    task_id: UUID,
    data: ReviewTaskAssign,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Assign a review task to a user."""
    try:
        task = await review_queue_service.assign_task(db, task_id, data.assigned_to_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return task


@router.post(
    "/review-tasks/{task_id}/complete",
    response_model=ReviewTaskRead,
    tags=["Review Queue"],
)
async def complete_review_task(
    task_id: UUID,
    data: ReviewTaskComplete,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Complete a review task with a resolution."""
    try:
        task = await review_queue_service.complete_task(
            db, task_id, current_user.id, data.resolution, data.resolution_note
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return task


@router.post(
    "/review-tasks/{task_id}/escalate",
    response_model=ReviewTaskRead,
    tags=["Review Queue"],
)
async def escalate_review_task(
    task_id: UUID,
    data: ReviewTaskEscalate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Escalate a review task."""
    try:
        task = await review_queue_service.escalate_task(db, task_id, data.escalation_reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return task
