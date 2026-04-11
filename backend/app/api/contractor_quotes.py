"""Contractor Quote Extraction API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.contractor_quote import ContractorQuote
from app.models.user import User
from app.schemas.contractor_quote import (
    ContractorQuoteCreate,
    ContractorQuoteList,
    ContractorQuoteRead,
    ContractorQuoteUpdate,
)

router = APIRouter()


@router.post(
    "/documents/{document_id}/extract-quote",
    response_model=ContractorQuoteRead,
    status_code=201,
)
async def extract_quote_from_document(
    document_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Extract contractor quote from document using LLM."""
    from app.services.quote_extraction_service import extract_quote_from_document as extract_service

    # Verify document exists
    stmt = select(ContractorQuote).where(ContractorQuote.document_id == document_id)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Quote already extracted for this document")

    # Extract quote
    try:
        quote = await extract_service(db, document_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extraction failed: {str(e)}") from e

    await db.commit()
    return quote


@router.get("/buildings/{building_id}/quotes", response_model=list[ContractorQuoteList])
async def list_building_quotes(
    building_id: UUID,
    reviewed: str | None = Query(None, pattern="^(pending|confirmed|disputed)$"),
    min_confidence: float = Query(0.0, ge=0, le=1),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List contractor quotes for a building."""
    stmt = select(ContractorQuote).where(ContractorQuote.building_id == building_id)

    if reviewed:
        stmt = stmt.where(ContractorQuote.reviewed == reviewed)

    if min_confidence > 0:
        stmt = stmt.where(ContractorQuote.confidence >= min_confidence)

    stmt = stmt.order_by(ContractorQuote.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    quotes = list(result.scalars().all())
    return quotes


@router.get("/quotes/{quote_id}", response_model=ContractorQuoteRead)
async def get_quote(
    quote_id: UUID,
    current_user: User = Depends(require_permission("documents", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get contractor quote by ID."""
    stmt = select(ContractorQuote).where(ContractorQuote.id == quote_id)
    result = await db.execute(stmt)
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    return quote


@router.patch("/quotes/{quote_id}", response_model=ContractorQuoteRead)
async def update_quote_review(
    quote_id: UUID,
    body: ContractorQuoteUpdate,
    current_user: User = Depends(require_permission("documents", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update quote review status and notes."""
    stmt = select(ContractorQuote).where(ContractorQuote.id == quote_id)
    result = await db.execute(stmt)
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    quote.reviewed = body.reviewed
    quote.reviewer_notes = body.reviewer_notes
    quote.reviewed_by = current_user.id
    from datetime import datetime as dt

    quote.reviewed_at = dt.now()

    await db.commit()
    return quote


@router.get("/analytics/quotes", response_model=dict)
async def get_quote_extraction_metrics(
    building_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get quote extraction metrics."""
    stmt = select(ContractorQuote)
    if building_id:
        stmt = stmt.where(ContractorQuote.building_id == building_id)

    result = await db.execute(stmt)
    quotes = list(result.scalars().all())

    total = len(quotes)
    high_confidence = sum(1 for q in quotes if q.confidence >= 0.7)
    low_confidence = sum(1 for q in quotes if q.confidence < 0.7)
    reviewed = sum(1 for q in quotes if q.reviewed != "pending")
    avg_confidence = sum(q.confidence for q in quotes) / total if total > 0 else 0

    return {
        "total_quotes": total,
        "high_confidence_count": high_confidence,
        "low_confidence_count": low_confidence,
        "average_confidence": round(avg_confidence, 3),
        "reviewed_count": reviewed,
        "pending_review": total - reviewed,
    }
