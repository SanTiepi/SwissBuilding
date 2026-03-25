"""BatiConnect — AI Extraction service (provider-backed).

Uses AIProviderBase adapter: OpenAI when OPENAI_API_KEY set, stub otherwise.
On provider failure: status="failed", error_message populated, never fakes success.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_extraction_log import AIExtractionLog
from app.models.ai_feedback import AIFeedback
from app.schemas.growth_stack import CompletionExtractionDraft, QuoteExtractionDraft
from app.schemas.intelligence_stack import CertificateExtractionDraft
from app.services.ai_provider import get_ai_provider, get_prompt_version

logger = logging.getLogger(__name__)


def _hash_input(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Provider-backed extraction
# ---------------------------------------------------------------------------


async def _run_extraction(
    db: AsyncSession,
    *,
    extraction_type: str,
    text: str | None = None,
    source_filename: str | None = None,
    source_document_id: uuid.UUID | None = None,
    schema_hint: dict | None = None,
) -> tuple[AIExtractionLog, dict]:
    """Run extraction via provider adapter. On failure: status=failed, never fake."""
    input_text = text or source_filename or "empty"
    input_hash = _hash_input(input_text)

    provider = get_ai_provider()
    start = time.monotonic()
    error_message = None
    output_data = None
    confidence_score = None
    ambiguous_fields = None
    unknown_fields = None
    status = "draft"

    try:
        result = provider.extract(input_text, extraction_type, schema_hint)
        # Handle both sync and async
        if hasattr(result, "__await__"):
            result = await result

        output_data = result.get("fields", {})
        confidence_score = result.get("confidence", 0.0)
        ambiguous_fields = result.get("ambiguous", [])
        unknown_fields = result.get("unknown", [])
    except Exception as exc:
        logger.exception("AI extraction failed: provider=%s type=%s", provider.provider_name, extraction_type)
        status = "failed"
        error_message = str(exc)[:2000]

    latency_ms = int((time.monotonic() - start) * 1000)

    log = AIExtractionLog(
        extraction_type=extraction_type,
        source_document_id=source_document_id,
        source_filename=source_filename,
        input_hash=input_hash,
        output_data=output_data,
        confidence_score=confidence_score,
        ai_model=provider.model_version,
        ambiguous_fields=ambiguous_fields,
        unknown_fields=unknown_fields,
        status=status,
        provider_name=provider.provider_name,
        model_version=provider.model_version,
        prompt_version=get_prompt_version(),
        latency_ms=latency_ms,
        error_message=error_message,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log, output_data or {}


# ---------------------------------------------------------------------------
# Public extraction functions
# ---------------------------------------------------------------------------


async def extract_quote_data(
    db: AsyncSession,
    *,
    text: str | None = None,
    source_filename: str | None = None,
    source_document_id: uuid.UUID | None = None,
) -> tuple[AIExtractionLog, QuoteExtractionDraft]:
    """Extract structured data from a remediation quote."""
    log, fields = await _run_extraction(
        db,
        extraction_type="quote_pdf",
        text=text,
        source_filename=source_filename,
        source_document_id=source_document_id,
    )

    if log.status == "failed":
        draft = QuoteExtractionDraft(
            scope_items=[],
            exclusions=[],
            confidence_per_field={},
            ambiguous_fields=[],
            unknown_fields=[],
        )
    else:
        draft = QuoteExtractionDraft(
            scope_items=fields.get("scope_items", []),
            exclusions=fields.get("exclusions", []),
            timeline_weeks=fields.get("timeline_weeks"),
            amount_chf=fields.get("amount_chf"),
            confidence_per_field={k: log.confidence_score or 0.0 for k in fields if k != "exclusions"},
            ambiguous_fields=log.ambiguous_fields or [],
            unknown_fields=log.unknown_fields or [],
        )

    return log, draft


async def extract_completion_data(
    db: AsyncSession,
    *,
    text: str | None = None,
    source_filename: str | None = None,
    source_document_id: uuid.UUID | None = None,
) -> tuple[AIExtractionLog, CompletionExtractionDraft]:
    """Extract structured data from a completion report."""
    log, fields = await _run_extraction(
        db,
        extraction_type="completion_report",
        text=text,
        source_filename=source_filename,
        source_document_id=source_document_id,
    )

    if log.status == "failed":
        draft = CompletionExtractionDraft(
            completed_items=[],
            residual_items=[],
            confidence_per_field={},
            ambiguous_fields=[],
            unknown_fields=[],
        )
    else:
        draft = CompletionExtractionDraft(
            completed_items=fields.get("completed_items", []),
            residual_items=fields.get("residual_items", []),
            final_amount_chf=fields.get("final_amount_chf"),
            confidence_per_field={k: log.confidence_score or 0.0 for k in fields},
            ambiguous_fields=log.ambiguous_fields or [],
            unknown_fields=log.unknown_fields or [],
        )

    return log, draft


async def extract_certificate_data(
    db: AsyncSession,
    input_text: str,
    source_doc_id: uuid.UUID | None = None,
) -> tuple[AIExtractionLog, CertificateExtractionDraft]:
    """Extract structured data from a certificate/clearance document."""
    log, fields = await _run_extraction(
        db,
        extraction_type="certificate",
        text=input_text,
        source_document_id=source_doc_id,
    )

    if log.status == "failed":
        draft = CertificateExtractionDraft(
            certificate_type=None,
            issuer=None,
            date_issued=None,
            building_ref=None,
            pollutant=None,
            result=None,
            confidence_per_field={},
            ambiguous_fields=[],
            unknown_fields=[],
        )
    else:
        draft = CertificateExtractionDraft(
            certificate_type=fields.get("certificate_type"),
            issuer=fields.get("issuer"),
            date_issued=fields.get("date_issued"),
            building_ref=fields.get("building_ref"),
            pollutant=fields.get("pollutant"),
            result=fields.get("result"),
            confidence_per_field={k: log.confidence_score or 0.0 for k in fields},
            ambiguous_fields=log.ambiguous_fields or [],
            unknown_fields=log.unknown_fields or [],
        )

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
