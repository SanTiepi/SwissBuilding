"""Flywheel learning loop API — classification & extraction feedback endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.flywheel import (
    ClassificationFeedbackCreate,
    ExtractionFeedbackCreate,
    FlywheelDashboardRead,
    LearnedRule,
)

router = APIRouter()


@router.post("/flywheel/classification-feedback")
async def record_classification_feedback(
    body: ClassificationFeedbackCreate,
    current_user: User = Depends(require_permission("documents", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Record a human correction on document classification."""
    from app.services.flywheel_service import record_classification_feedback as _record

    result = await _record(
        db,
        document_id=UUID(body.document_id),
        predicted_type=body.predicted_type,
        corrected_type=body.corrected_type,
        user_id=current_user.id,
    )
    await db.commit()
    return result


@router.post("/flywheel/extraction-feedback")
async def record_extraction_feedback(
    body: ExtractionFeedbackCreate,
    current_user: User = Depends(require_permission("documents", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Record a human correction or confirmation on an extracted field."""
    from app.services.flywheel_service import record_extraction_feedback as _record

    result = await _record(
        db,
        document_id=UUID(body.document_id),
        field_name=body.field_name,
        predicted_value=body.predicted_value,
        corrected_value=body.corrected_value,
        accepted=body.accepted,
        user_id=current_user.id,
    )
    await db.commit()
    return result


@router.get("/flywheel/accuracy/classification")
async def get_classification_accuracy(
    org_id: str | None = None,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get classification accuracy metrics."""
    from app.services.flywheel_service import get_classification_accuracy as _get

    return await _get(db, org_id=UUID(org_id) if org_id else None)


@router.get("/flywheel/accuracy/extraction")
async def get_extraction_accuracy(
    org_id: str | None = None,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get extraction accuracy metrics."""
    from app.services.flywheel_service import get_extraction_accuracy as _get

    return await _get(db, org_id=UUID(org_id) if org_id else None)


@router.get("/flywheel/learned-rules", response_model=list[LearnedRule])
async def get_learned_rules(
    document_type: str | None = None,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get learned rules discovered from correction patterns."""
    from app.services.flywheel_service import get_learning_rules as _get

    return await _get(db, document_type=document_type)


@router.get("/flywheel/dashboard", response_model=FlywheelDashboardRead)
async def get_flywheel_dashboard(
    org_id: str | None = None,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the full flywheel learning dashboard."""
    from app.services.flywheel_service import get_flywheel_dashboard as _get

    return await _get(db, org_id=UUID(org_id) if org_id else None)
