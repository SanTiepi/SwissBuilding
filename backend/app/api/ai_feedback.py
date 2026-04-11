"""AI Feedback Loop API — correction recording + accuracy metrics."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.ai_feedback import AIFeedbackCreate, AIFeedbackRead, AIMetricsRead, AIMetricsSummary

router = APIRouter()


@router.post("/diagnostics/{diagnostic_id}/feedback", response_model=AIFeedbackRead, status_code=201)
async def record_diagnostic_feedback(
    diagnostic_id: UUID,
    body: AIFeedbackCreate,
    current_user: User = Depends(require_permission("diagnostics", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a human correction on an AI-extracted diagnostic field."""
    from app.services.ai_feedback_service import record_feedback

    feedback = await record_feedback(
        db,
        entity_type=body.entity_type,
        entity_id=body.entity_id or diagnostic_id,
        field_name=body.field_name,
        original_value=body.original_value,
        corrected_value=body.corrected_value,
        model_version=body.model_version,
        user_id=current_user.id,
        notes=body.notes,
    )
    await db.commit()
    return feedback


@router.get("/analytics/ai-metrics", response_model=AIMetricsSummary)
async def get_ai_metrics(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated AI accuracy metrics — admin dashboard."""
    from app.services.ai_feedback_service import get_metrics_summary

    return await get_metrics_summary(db, entity_type=entity_type)


@router.get("/analytics/ai-metrics/{entity_type}", response_model=list[AIMetricsRead])
async def get_ai_metrics_by_type(
    entity_type: str,
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get AI metrics filtered by entity type."""
    from app.services.ai_feedback_service import get_metrics

    return await get_metrics(db, entity_type=entity_type)


@router.get("/analytics/ai-feedback", response_model=list[AIFeedbackRead])
async def list_ai_feedback(
    entity_type: str | None = Query(None),
    entity_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List recent AI feedback records."""
    from app.services.ai_feedback_service import list_feedback

    return await list_feedback(db, entity_type=entity_type, entity_id=entity_id, limit=limit)
