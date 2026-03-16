"""Document classification API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.document_classification import (
    ClassificationSummary,
    DocumentClassification,
    MissingDocumentSuggestion,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/buildings/{building_id}/documents/classify",
    response_model=list[DocumentClassification],
)
async def classify_building_documents_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Classify all documents for a building."""
    await _get_building_or_404(db, building_id)

    from app.services.document_classification_service import classify_building_documents

    return await classify_building_documents(db, building_id)


@router.get(
    "/buildings/{building_id}/documents/classification-summary",
    response_model=ClassificationSummary,
)
async def classification_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get classification summary for a building's documents."""
    await _get_building_or_404(db, building_id)

    from app.services.document_classification_service import get_classification_summary

    return await get_classification_summary(db, building_id)


@router.get(
    "/buildings/{building_id}/documents/missing-documents",
    response_model=list[MissingDocumentSuggestion],
)
async def missing_documents_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Suggest missing documents based on diagnostics and pollutants."""
    await _get_building_or_404(db, building_id)

    from app.services.document_classification_service import suggest_missing_documents

    return await suggest_missing_documents(db, building_id)
