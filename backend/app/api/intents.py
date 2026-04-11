"""Building Intent & Question API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models.building_intent import BuildingIntent, BuildingQuestion
from app.models.user import User
from app.schemas.building_intent import (
    BuildingIntentCreate,
    BuildingIntentRead,
    BuildingQuestionCreate,
    BuildingQuestionRead,
    QuestionWithAnswer,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Intents
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/intents",
    response_model=BuildingIntentRead,
    status_code=201,
)
async def create_intent_endpoint(
    building_id: UUID,
    data: BuildingIntentCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new building intent. Auto-generates relevant questions."""
    await _get_building_or_404(db, building_id)

    from app.services.intent_service import create_intent

    try:
        intent = await create_intent(
            db,
            building_id=building_id,
            intent_type=data.intent_type,
            created_by_id=current_user.id,
            title=data.title,
            organization_id=data.organization_id,
            description=data.description,
            target_date=data.target_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return intent


@router.get(
    "/buildings/{building_id}/intents",
    response_model=PaginatedResponse[BuildingIntentRead],
)
async def list_intents_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all intents for a building."""
    await _get_building_or_404(db, building_id)

    query = select(BuildingIntent).where(BuildingIntent.building_id == building_id)
    count_query = select(func.count()).select_from(BuildingIntent).where(BuildingIntent.building_id == building_id)

    if status:
        query = query.where(BuildingIntent.status == status)
        count_query = count_query.where(BuildingIntent.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(BuildingIntent.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/questions",
    response_model=BuildingQuestionRead,
    status_code=201,
)
async def ask_question_endpoint(
    building_id: UUID,
    data: BuildingQuestionCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Ask a question about a building."""
    await _get_building_or_404(db, building_id)

    from app.services.intent_service import ask_question

    try:
        question = await ask_question(
            db,
            building_id=building_id,
            question_type=data.question_type,
            asked_by_id=current_user.id,
            intent_id=data.intent_id,
            question_text=data.question_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return question


@router.get(
    "/buildings/{building_id}/questions/{question_id}",
    response_model=QuestionWithAnswer,
)
async def get_question_endpoint(
    building_id: UUID,
    question_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a question with its answer (decision context + safe-to-x verdict)."""
    await _get_building_or_404(db, building_id)

    result = await db.execute(
        select(BuildingQuestion)
        .options(
            selectinload(BuildingQuestion.decision_context),
            selectinload(BuildingQuestion.safe_to_x_state),
        )
        .where(
            BuildingQuestion.id == question_id,
            BuildingQuestion.building_id == building_id,
        )
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return QuestionWithAnswer(
        question=BuildingQuestionRead.model_validate(question),
        decision_context=question.decision_context,
        safe_to_x_state=question.safe_to_x_state,
    )


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------


@router.post(
    "/questions/{question_id}/evaluate",
    response_model=QuestionWithAnswer,
)
async def evaluate_question_endpoint(
    question_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger evaluation of a question."""
    from app.services.intent_service import evaluate_question

    try:
        question = await evaluate_question(db, question_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    # Reload with relations
    result = await db.execute(
        select(BuildingQuestion)
        .options(
            selectinload(BuildingQuestion.decision_context),
            selectinload(BuildingQuestion.safe_to_x_state),
        )
        .where(BuildingQuestion.id == question_id)
    )
    question = result.scalar_one_or_none()

    return QuestionWithAnswer(
        question=BuildingQuestionRead.model_validate(question),
        decision_context=question.decision_context,
        safe_to_x_state=question.safe_to_x_state,
    )


# ---------------------------------------------------------------------------
# SafeToX summary
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/safe-to-x",
)
async def get_safe_to_x_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all SafeToX verdicts for a building (unified readiness + transaction)."""
    await _get_building_or_404(db, building_id)

    from app.services.intent_service import get_safe_to_x_summary

    return await get_safe_to_x_summary(db, building_id)
