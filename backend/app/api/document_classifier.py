"""Document classifier API — hybrid classification pipeline endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.document_classifier import (
    BatchClassificationResult,
    ClassificationResult,
    DocumentTypeInfo,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/documents/{document_id}/classify",
    response_model=ClassificationResult,
)
async def classify_single_document(
    document_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Classify a single document using the hybrid pipeline."""
    from app.services.document_classifier_service import classify_and_update

    try:
        result = await classify_and_update(db, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ClassificationResult(**result)


@router.post(
    "/buildings/{building_id}/documents/classify-all",
    response_model=BatchClassificationResult,
)
async def batch_classify_building_documents(
    building_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Batch classify all unclassified documents for a building."""
    await _get_building_or_404(db, building_id)

    from app.services.document_classifier_service import batch_classify

    results = await batch_classify(db, building_id)
    classified = [r for r in results if r.get("document_type") != "unclassified"]

    return BatchClassificationResult(
        building_id=str(building_id),
        total_processed=len(results),
        classified_count=len(classified),
        unclassified_count=len(results) - len(classified),
        results=[ClassificationResult(**r) for r in results],
    )


@router.get(
    "/documents/types",
    response_model=list[DocumentTypeInfo],
)
async def list_document_types(
    current_user: User = Depends(require_permission("documents", "read")),
):
    """List all 10 supported document types with descriptions."""
    from app.services.document_classifier_service import DOCUMENT_TYPES

    return [
        DocumentTypeInfo(
            type_key=key,
            label_fr=spec["label_fr"],
            label_en=spec["label_en"],
            label_de=spec["label_de"],
            label_it=spec["label_it"],
            keywords=spec["keywords"],
        )
        for key, spec in DOCUMENT_TYPES.items()
    ]
