"""Unknown issue management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.unknown_issue import UnknownIssue
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.unknown_issue import (
    UnknownIssueCreate,
    UnknownIssueRead,
    UnknownIssueUpdate,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_issue_or_404(db: AsyncSession, building_id: UUID, issue_id: UUID) -> UnknownIssue:
    result = await db.execute(
        select(UnknownIssue).where(
            UnknownIssue.id == issue_id,
            UnknownIssue.building_id == building_id,
        )
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Unknown issue not found")
    return issue


@router.get(
    "/buildings/{building_id}/unknowns",
    response_model=PaginatedResponse[UnknownIssueRead],
)
async def list_unknowns_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    unknown_type: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    current_user: User = Depends(require_permission("unknowns", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List unknown issues for a building."""
    await _get_building_or_404(db, building_id)

    query = select(UnknownIssue).where(UnknownIssue.building_id == building_id)
    count_query = select(func.count()).select_from(UnknownIssue).where(UnknownIssue.building_id == building_id)

    if unknown_type:
        query = query.where(UnknownIssue.unknown_type == unknown_type)
        count_query = count_query.where(UnknownIssue.unknown_type == unknown_type)
    if status:
        query = query.where(UnknownIssue.status == status)
        count_query = count_query.where(UnknownIssue.status == status)
    if severity:
        query = query.where(UnknownIssue.severity == severity)
        count_query = count_query.where(UnknownIssue.severity == severity)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(UnknownIssue.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post(
    "/buildings/{building_id}/unknowns",
    response_model=UnknownIssueRead,
    status_code=201,
)
async def create_unknown_endpoint(
    building_id: UUID,
    data: UnknownIssueCreate,
    current_user: User = Depends(require_permission("unknowns", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new unknown issue."""
    await _get_building_or_404(db, building_id)

    issue = UnknownIssue(
        building_id=building_id,
        **data.model_dump(),
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


@router.get(
    "/buildings/{building_id}/unknowns/{issue_id}",
    response_model=UnknownIssueRead,
)
async def get_unknown_endpoint(
    building_id: UUID,
    issue_id: UUID,
    current_user: User = Depends(require_permission("unknowns", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single unknown issue."""
    await _get_building_or_404(db, building_id)
    return await _get_issue_or_404(db, building_id, issue_id)


@router.put(
    "/buildings/{building_id}/unknowns/{issue_id}",
    response_model=UnknownIssueRead,
)
async def update_unknown_endpoint(
    building_id: UUID,
    issue_id: UUID,
    data: UnknownIssueUpdate,
    current_user: User = Depends(require_permission("unknowns", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an unknown issue."""
    await _get_building_or_404(db, building_id)
    issue = await _get_issue_or_404(db, building_id, issue_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(issue, key, value)

    await db.commit()
    await db.refresh(issue)
    return issue


@router.delete(
    "/buildings/{building_id}/unknowns/{issue_id}",
    status_code=204,
)
async def delete_unknown_endpoint(
    building_id: UUID,
    issue_id: UUID,
    current_user: User = Depends(require_permission("unknowns", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete an unknown issue."""
    await _get_building_or_404(db, building_id)
    issue = await _get_issue_or_404(db, building_id, issue_id)
    await db.delete(issue)
    await db.commit()
