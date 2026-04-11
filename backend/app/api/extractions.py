"""Diagnostic extraction API endpoints.

Flow: POST extract -> GET review -> PUT update -> POST apply (or POST reject).
Never auto-persists. Every correction feeds ai_feedback.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.diagnostic_extraction import (
    DiagnosticExtractionApplyResponse,
    DiagnosticExtractionCorrectionCreate,
    DiagnosticExtractionRead,
    DiagnosticExtractionRejectRequest,
    DiagnosticExtractionReview,
)
from app.services import diagnostic_extraction_service as svc

router = APIRouter()


async def _get_document_or_404(db: AsyncSession, document_id: UUID):
    from sqlalchemy import select

    from app.models.document import Document

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post(
    "/documents/{document_id}/extract",
    response_model=DiagnosticExtractionRead,
    status_code=201,
    tags=["Diagnostic Extraction"],
)
async def trigger_extraction_endpoint(
    document_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger diagnostic extraction from a document.

    Reads the document's text content and extracts structured diagnostic data.
    Returns a draft extraction for human review. NEVER auto-persists.
    """
    doc = await _get_document_or_404(db, document_id)

    # Read the document text (from MinIO or file system via processing metadata)
    # For rule-based extraction, we need the OCR'd text content.
    # The text should be provided or retrieved from storage.
    # For now, we attempt to read from the file path.
    text = await _read_document_text(doc)
    if not text:
        raise HTTPException(
            status_code=422,
            detail="Cannot extract text from document. Ensure the document is a PDF that has been OCR-processed.",
        )

    try:
        extraction = await svc.extract_from_document(
            db,
            document_id=document_id,
            building_id=doc.building_id,
            created_by_id=current_user.id,
            text=text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await db.commit()
    await db.refresh(extraction)
    return extraction


@router.get(
    "/extractions/{extraction_id}",
    response_model=DiagnosticExtractionRead,
    tags=["Diagnostic Extraction"],
)
async def get_extraction_endpoint(
    extraction_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a diagnostic extraction result."""
    extraction = await svc.get_extraction(db, extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return extraction


@router.put(
    "/extractions/{extraction_id}/review",
    response_model=DiagnosticExtractionRead,
    tags=["Diagnostic Extraction"],
)
async def review_extraction_endpoint(
    extraction_id: UUID,
    data: DiagnosticExtractionReview,
    current_user: User = Depends(require_permission("diagnostics", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Review and optionally update an extraction before applying."""
    try:
        extraction = await svc.review_extraction(
            db,
            extraction_id=extraction_id,
            reviewed_by_id=current_user.id,
            updated_data=data.extracted_data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await db.commit()
    await db.refresh(extraction)
    return extraction


@router.post(
    "/extractions/{extraction_id}/apply",
    response_model=DiagnosticExtractionApplyResponse,
    tags=["Diagnostic Extraction"],
)
async def apply_extraction_endpoint(
    extraction_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Apply a reviewed extraction to the database.

    Creates Diagnostic, Samples, and EvidenceLinks.
    This is the final step in parse -> review -> apply.
    """
    try:
        result = await svc.apply_extraction(
            db,
            extraction_id=extraction_id,
            applied_by_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await db.commit()
    return result


@router.post(
    "/extractions/{extraction_id}/reject",
    response_model=DiagnosticExtractionRead,
    tags=["Diagnostic Extraction"],
)
async def reject_extraction_endpoint(
    extraction_id: UUID,
    data: DiagnosticExtractionRejectRequest | None = None,
    current_user: User = Depends(require_permission("diagnostics", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Reject an extraction. Records feedback for the AI flywheel."""
    reason = data.reason if data else None
    try:
        extraction = await svc.reject_extraction(
            db,
            extraction_id=extraction_id,
            rejected_by_id=current_user.id,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await db.commit()
    await db.refresh(extraction)
    return extraction


@router.post(
    "/extractions/{extraction_id}/corrections",
    response_model=DiagnosticExtractionRead,
    tags=["Diagnostic Extraction"],
)
async def record_correction_endpoint(
    extraction_id: UUID,
    data: DiagnosticExtractionCorrectionCreate,
    current_user: User = Depends(require_permission("diagnostics", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a human correction to an extraction field.

    Feeds the ai_feedback loop for future improvement.
    """
    try:
        extraction = await svc.record_correction(
            db,
            extraction_id=extraction_id,
            field_path=data.field_path,
            old_value=data.old_value,
            new_value=data.new_value,
            corrected_by_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await db.commit()
    await db.refresh(extraction)
    return extraction


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _read_document_text(doc) -> str | None:
    """Read text content from a document.

    Attempts to read the PDF file and extract text using PyMuPDF (if available)
    or falls back to basic text extraction.
    """
    import os

    from app.config import settings

    # Build file path from MinIO/local storage
    file_path = doc.file_path
    if not file_path:
        return None

    # Try local file path first (dev environment)
    full_path = os.path.join(settings.UPLOAD_DIR, file_path) if hasattr(settings, "UPLOAD_DIR") else file_path

    if not os.path.exists(full_path):
        # In production, file might be in MinIO -- return None to signal
        # that text extraction needs the file content
        return None

    # Try PyMuPDF for PDF text extraction
    try:
        import fitz  # PyMuPDF

        pdf_doc = fitz.open(full_path)
        text_parts = []
        for page in pdf_doc:
            text_parts.append(page.get_text())
        pdf_doc.close()
        text = "\n".join(text_parts)
        return text if text.strip() else None
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: try reading as plain text
    try:
        with open(full_path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return text if text.strip() else None
    except Exception:
        return None
