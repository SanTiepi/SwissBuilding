"""Document extraction API routes (GED B).

POST /documents/{document_id}/extract — extract structured data from document text
GET  /documents/{document_id}/extractions — get stored extractions
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.document import Document
from app.models.user import User
from app.schemas.document_extraction import ExtractionResult

router = APIRouter()


async def _get_document_or_404(db: AsyncSession, document_id: UUID) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post(
    "/documents/{document_id}/extract-fields",
    response_model=ExtractionResult,
    status_code=200,
    tags=["Document Extraction"],
)
async def extract_document_fields(
    document_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Extract structured data (dates, amounts, addresses, etc.) from a document's text."""
    await _get_document_or_404(db, document_id)

    from app.services.document_extraction_service import extract_and_store

    try:
        result = await extract_and_store(db, document_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    await db.commit()
    return result


@router.get(
    "/documents/{document_id}/extractions",
    response_model=ExtractionResult | None,
    tags=["Document Extraction"],
)
async def get_document_extractions(
    document_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get stored extractions for a document."""
    doc = await _get_document_or_404(db, document_id)

    meta = doc.processing_metadata or {}
    ext = meta.get("extractions")
    if not ext:
        return None

    fields = ext.get("fields", {})
    return ExtractionResult(
        document_id=str(document_id),
        total_fields=ext.get("total_fields", 0),
        field_counts={k: len(v) for k, v in fields.items()},
        extractions=fields,
    )
