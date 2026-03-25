"""BatiConnect — AI Extraction service (stub — real LLM integration is Phase 2)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_extraction_log import AIExtractionLog
from app.models.ai_feedback import AIFeedback
from app.schemas.growth_stack import CompletionExtractionDraft, QuoteExtractionDraft

# ---------------------------------------------------------------------------
# Stub extraction (mock data — no LLM call)
# ---------------------------------------------------------------------------

_STUB_MODEL = "stub-v0"


def _hash_input(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def extract_quote_data(
    db: AsyncSession,
    *,
    text: str | None = None,
    source_filename: str | None = None,
    source_document_id: uuid.UUID | None = None,
) -> tuple[AIExtractionLog, QuoteExtractionDraft]:
    """Stub: returns mock quote extraction. Real LLM is Phase 2."""
    input_text = text or source_filename or "empty"
    input_hash = _hash_input(input_text)

    draft = QuoteExtractionDraft(
        scope_items=["asbestos_removal", "waste_disposal", "air_monitoring"],
        exclusions=["scaffolding", "permits"],
        timeline_weeks=6,
        amount_chf=45000.0,
        confidence_per_field={
            "scope_items": 0.85,
            "exclusions": 0.75,
            "timeline_weeks": 0.70,
            "amount_chf": 0.90,
        },
        ambiguous_fields=[{"field": "timeline_weeks", "reason": "Multiple timelines mentioned"}],
        unknown_fields=[{"field": "payment_terms"}],
    )

    log = AIExtractionLog(
        extraction_type="quote_pdf",
        source_document_id=source_document_id,
        source_filename=source_filename,
        input_hash=input_hash,
        output_data=draft.model_dump(),
        confidence_score=0.80,
        ai_model=_STUB_MODEL,
        ambiguous_fields=draft.ambiguous_fields,
        unknown_fields=draft.unknown_fields,
        status="draft",
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log, draft


async def extract_completion_data(
    db: AsyncSession,
    *,
    text: str | None = None,
    source_filename: str | None = None,
    source_document_id: uuid.UUID | None = None,
) -> tuple[AIExtractionLog, CompletionExtractionDraft]:
    """Stub: returns mock completion extraction. Real LLM is Phase 2."""
    input_text = text or source_filename or "empty"
    input_hash = _hash_input(input_text)

    draft = CompletionExtractionDraft(
        completed_items=["asbestos_removal", "waste_disposal", "final_report"],
        residual_items=["air_monitoring_post"],
        final_amount_chf=43500.0,
        confidence_per_field={
            "completed_items": 0.90,
            "residual_items": 0.65,
            "final_amount_chf": 0.95,
        },
        ambiguous_fields=[{"field": "residual_items", "reason": "Partial completion noted"}],
        unknown_fields=[],
    )

    log = AIExtractionLog(
        extraction_type="completion_report",
        source_document_id=source_document_id,
        source_filename=source_filename,
        input_hash=input_hash,
        output_data=draft.model_dump(),
        confidence_score=0.85,
        ai_model=_STUB_MODEL,
        ambiguous_fields=draft.ambiguous_fields,
        unknown_fields=draft.unknown_fields,
        status="draft",
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log, draft


# ---------------------------------------------------------------------------
# Confirm / Correct / Reject
# ---------------------------------------------------------------------------


async def get_extraction_log(db: AsyncSession, log_id: uuid.UUID) -> AIExtractionLog | None:
    result = await db.execute(select(AIExtractionLog).where(AIExtractionLog.id == log_id))
    return result.scalar_one_or_none()


async def confirm_extraction(db: AsyncSession, log_id: uuid.UUID, user_id: uuid.UUID) -> AIExtractionLog:
    log = await get_extraction_log(db, log_id)
    if log is None:
        raise ValueError("Extraction log not found")

    log.status = "confirmed"
    log.confirmed_by_user_id = user_id
    log.confirmed_at = datetime.now(UTC)

    feedback = AIFeedback(
        feedback_type="confirm",
        entity_type="extraction",
        entity_id=log.id,
        original_output=log.output_data,
        ai_model=log.ai_model,
        confidence=log.confidence_score,
        user_id=user_id,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(log)
    return log


async def correct_extraction(
    db: AsyncSession,
    log_id: uuid.UUID,
    corrected_data: dict,
    user_id: uuid.UUID,
    notes: str | None = None,
) -> AIExtractionLog:
    log = await get_extraction_log(db, log_id)
    if log is None:
        raise ValueError("Extraction log not found")

    original = log.output_data

    log.status = "corrected"
    log.output_data = corrected_data
    log.confirmed_by_user_id = user_id
    log.confirmed_at = datetime.now(UTC)

    feedback = AIFeedback(
        feedback_type="correct",
        entity_type="extraction",
        entity_id=log.id,
        original_output=original,
        corrected_output=corrected_data,
        ai_model=log.ai_model,
        confidence=log.confidence_score,
        user_id=user_id,
        notes=notes,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(log)
    return log


async def reject_extraction(
    db: AsyncSession,
    log_id: uuid.UUID,
    user_id: uuid.UUID,
    reason: str | None = None,
) -> AIExtractionLog:
    log = await get_extraction_log(db, log_id)
    if log is None:
        raise ValueError("Extraction log not found")

    log.status = "rejected"
    log.confirmed_by_user_id = user_id
    log.confirmed_at = datetime.now(UTC)

    feedback = AIFeedback(
        feedback_type="reject",
        entity_type="extraction",
        entity_id=log.id,
        original_output=log.output_data,
        ai_model=log.ai_model,
        confidence=log.confidence_score,
        user_id=user_id,
        notes=reason,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(log)
    return log
