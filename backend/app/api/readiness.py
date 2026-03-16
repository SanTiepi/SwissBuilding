"""Readiness assessment management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.readiness_assessment import ReadinessAssessment
from app.models.user import User
from app.schemas.action_item import ActionItemRead
from app.schemas.common import PaginatedResponse
from app.schemas.readiness import (
    PreworkTrigger,
    ReadinessAssessmentCreate,
    ReadinessAssessmentRead,
    ReadinessAssessmentUpdate,
)
from app.services.readiness_action_generator import generate_readiness_actions

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_assessment_or_404(db: AsyncSession, building_id: UUID, assessment_id: UUID) -> ReadinessAssessment:
    result = await db.execute(
        select(ReadinessAssessment).where(
            ReadinessAssessment.id == assessment_id,
            ReadinessAssessment.building_id == building_id,
        )
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Readiness assessment not found")
    return assessment


@router.get(
    "/buildings/{building_id}/readiness",
    response_model=PaginatedResponse[ReadinessAssessmentRead],
)
async def list_readiness_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    readiness_type: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_permission("readiness", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List readiness assessments for a building."""
    await _get_building_or_404(db, building_id)

    query = select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    count_query = (
        select(func.count()).select_from(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    )

    if readiness_type:
        query = query.where(ReadinessAssessment.readiness_type == readiness_type)
        count_query = count_query.where(ReadinessAssessment.readiness_type == readiness_type)
    if status:
        query = query.where(ReadinessAssessment.status == status)
        count_query = count_query.where(ReadinessAssessment.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ReadinessAssessment.assessed_at.desc()).offset((page - 1) * size).limit(size)
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
    "/buildings/{building_id}/readiness",
    response_model=ReadinessAssessmentRead,
    status_code=201,
)
async def create_readiness_endpoint(
    building_id: UUID,
    data: ReadinessAssessmentCreate,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new readiness assessment."""
    await _get_building_or_404(db, building_id)

    assessment = ReadinessAssessment(
        building_id=building_id,
        assessed_by=current_user.id,
        **data.model_dump(),
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.get(
    "/buildings/{building_id}/readiness/{assessment_id}",
    response_model=ReadinessAssessmentRead,
)
async def get_readiness_endpoint(
    building_id: UUID,
    assessment_id: UUID,
    current_user: User = Depends(require_permission("readiness", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single readiness assessment."""
    await _get_building_or_404(db, building_id)
    return await _get_assessment_or_404(db, building_id, assessment_id)


@router.put(
    "/buildings/{building_id}/readiness/{assessment_id}",
    response_model=ReadinessAssessmentRead,
)
async def update_readiness_endpoint(
    building_id: UUID,
    assessment_id: UUID,
    data: ReadinessAssessmentUpdate,
    current_user: User = Depends(require_permission("readiness", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a readiness assessment."""
    await _get_building_or_404(db, building_id)
    assessment = await _get_assessment_or_404(db, building_id, assessment_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(assessment, key, value)

    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.delete(
    "/buildings/{building_id}/readiness/{assessment_id}",
    status_code=204,
)
async def delete_readiness_endpoint(
    building_id: UUID,
    assessment_id: UUID,
    current_user: User = Depends(require_permission("readiness", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a readiness assessment."""
    await _get_building_or_404(db, building_id)
    assessment = await _get_assessment_or_404(db, building_id, assessment_id)
    await db.delete(assessment)
    await db.commit()


@router.post(
    "/buildings/{building_id}/readiness/evaluate-all",
    response_model=list[ReadinessAssessmentRead],
)
async def evaluate_all_readiness_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate all 4 readiness types for a building."""
    from app.services.readiness_reasoner import evaluate_all_readiness

    await _get_building_or_404(db, building_id)
    assessments = await evaluate_all_readiness(db, building_id, current_user.id)
    return assessments


@router.get(
    "/buildings/{building_id}/readiness/{assessment_id}/prework-triggers",
    response_model=list[PreworkTrigger],
)
async def get_prework_triggers_endpoint(
    building_id: UUID,
    assessment_id: UUID,
    current_user: User = Depends(require_permission("readiness", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return deterministic prework triggers derived from a readiness assessment's checks."""
    await _get_building_or_404(db, building_id)
    assessment = await _get_assessment_or_404(db, building_id, assessment_id)
    read_schema = ReadinessAssessmentRead.model_validate(assessment)
    return read_schema.prework_triggers


@router.post(
    "/buildings/{building_id}/readiness/generate-actions",
    response_model=list[ActionItemRead],
)
async def generate_readiness_actions_endpoint(
    building_id: UUID,
    readiness_type: str | None = None,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Generate actions from blocked readiness checks."""
    await _get_building_or_404(db, building_id)
    actions = await generate_readiness_actions(db, building_id, readiness_type)
    await db.commit()
    for a in actions:
        await db.refresh(a)
    return actions
