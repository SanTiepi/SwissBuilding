"""
SwissBuildingOS - Assignments API

Manages user-to-target assignments (buildings, diagnostics).
"""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.assignment import Assignment
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentRead
from app.schemas.common import PaginatedResponse
from app.services.audit_service import log_action

router = APIRouter()


@router.get("/assignments", response_model=PaginatedResponse[AssignmentRead])
async def list_assignments(
    target_type: str | None = None,
    target_id: UUID | None = None,
    user_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("assignments", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List assignments with optional filters."""
    base = select(Assignment)

    if target_type is not None:
        base = base.where(Assignment.target_type == target_type)
    if target_id is not None:
        base = base.where(Assignment.target_id == target_id)
    if user_id is not None:
        base = base.where(Assignment.user_id == user_id)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * size
    data_stmt = base.order_by(Assignment.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(data_stmt)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.post("/assignments", response_model=AssignmentRead, status_code=201)
async def create_assignment(
    data: AssignmentCreate,
    current_user: User = Depends(require_permission("assignments", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new assignment."""
    assignment = Assignment(
        target_type=data.target_type,
        target_id=data.target_id,
        user_id=data.user_id,
        role=data.role,
        created_by=current_user.id,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    await log_action(db, current_user.id, "create", "assignment", assignment.id)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_permission("assignments", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete an assignment."""
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    await db.delete(assignment)
    await db.commit()
    await log_action(db, current_user.id, "delete", "assignment", assignment_id)
