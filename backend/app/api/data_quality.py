"""Data quality issue management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.data_quality_issue import DataQualityIssue
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.data_quality import (
    DataQualityIssueCreate,
    DataQualityIssueRead,
    DataQualityIssueUpdate,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_issue_or_404(db: AsyncSession, building_id: UUID, issue_id: UUID) -> DataQualityIssue:
    result = await db.execute(
        select(DataQualityIssue).where(
            DataQualityIssue.id == issue_id,
            DataQualityIssue.building_id == building_id,
        )
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Data quality issue not found")
    return issue


@router.get(
    "/buildings/{building_id}/data-quality-issues",
    response_model=PaginatedResponse[DataQualityIssueRead],
)
async def list_data_quality_issues_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    issue_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("data_quality", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List data quality issues for a building."""
    await _get_building_or_404(db, building_id)

    query = select(DataQualityIssue).where(DataQualityIssue.building_id == building_id)
    count_query = select(func.count()).select_from(DataQualityIssue).where(DataQualityIssue.building_id == building_id)

    if issue_type:
        query = query.where(DataQualityIssue.issue_type == issue_type)
        count_query = count_query.where(DataQualityIssue.issue_type == issue_type)
    if severity:
        query = query.where(DataQualityIssue.severity == severity)
        count_query = count_query.where(DataQualityIssue.severity == severity)
    if status:
        query = query.where(DataQualityIssue.status == status)
        count_query = count_query.where(DataQualityIssue.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DataQualityIssue.created_at.desc()).offset((page - 1) * size).limit(size)
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
    "/buildings/{building_id}/data-quality-issues",
    response_model=DataQualityIssueRead,
    status_code=201,
)
async def create_data_quality_issue_endpoint(
    building_id: UUID,
    data: DataQualityIssueCreate,
    current_user: User = Depends(require_permission("data_quality", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new data quality issue."""
    await _get_building_or_404(db, building_id)

    issue = DataQualityIssue(
        building_id=building_id,
        **data.model_dump(),
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


@router.get(
    "/buildings/{building_id}/data-quality-issues/{issue_id}",
    response_model=DataQualityIssueRead,
)
async def get_data_quality_issue_endpoint(
    building_id: UUID,
    issue_id: UUID,
    current_user: User = Depends(require_permission("data_quality", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single data quality issue."""
    await _get_building_or_404(db, building_id)
    return await _get_issue_or_404(db, building_id, issue_id)


@router.put(
    "/buildings/{building_id}/data-quality-issues/{issue_id}",
    response_model=DataQualityIssueRead,
)
async def update_data_quality_issue_endpoint(
    building_id: UUID,
    issue_id: UUID,
    data: DataQualityIssueUpdate,
    current_user: User = Depends(require_permission("data_quality", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a data quality issue."""
    await _get_building_or_404(db, building_id)
    issue = await _get_issue_or_404(db, building_id, issue_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(issue, key, value)

    await db.commit()
    await db.refresh(issue)
    return issue


@router.delete(
    "/buildings/{building_id}/data-quality-issues/{issue_id}",
    status_code=204,
)
async def delete_data_quality_issue_endpoint(
    building_id: UUID,
    issue_id: UUID,
    current_user: User = Depends(require_permission("data_quality", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a data quality issue."""
    await _get_building_or_404(db, building_id)
    issue = await _get_issue_or_404(db, building_id, issue_id)
    await db.delete(issue)
    await db.commit()


@router.post(
    "/buildings/{building_id}/contradictions/detect",
    response_model=list[DataQualityIssueRead],
)
async def detect_contradictions_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("data_quality", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Scan building data for contradictions and create DataQualityIssue records."""
    from app.services.contradiction_detector import detect_contradictions

    await _get_building_or_404(db, building_id)
    issues = await detect_contradictions(db, building_id)
    await db.commit()
    return issues


@router.get(
    "/buildings/{building_id}/contradictions/summary",
)
async def contradiction_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("data_quality", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Return summary of contradictions for a building."""
    from app.services.contradiction_detector import get_contradiction_summary

    await _get_building_or_404(db, building_id)
    return await get_contradiction_summary(db, building_id)
