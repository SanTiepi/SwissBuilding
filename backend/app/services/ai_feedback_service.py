"""BatiConnect — Programme I: AI Feedback Service — record corrections, aggregate metrics."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_feedback import AIFeedback
from app.models.ai_metrics import AIMetrics


async def record_feedback(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    field_name: str,
    original_value: str,
    corrected_value: str,
    user_id: UUID,
    model_version: str | None = None,
    notes: str | None = None,
) -> AIFeedback:
    """Record a human correction on an AI-extracted field."""
    confidence_delta = -0.15 if original_value != corrected_value else 0.0
    feedback_type = "correct" if original_value != corrected_value else "confirm"

    feedback = AIFeedback(
        id=uuid.uuid4(),
        feedback_type=feedback_type,
        entity_type=entity_type,
        entity_id=entity_id,
        field_name=field_name,
        original_value=original_value,
        corrected_value=corrected_value,
        confidence_delta=confidence_delta,
        model_version=model_version,
        user_id=user_id,
        notes=notes,
    )
    db.add(feedback)
    await db.flush()

    # Update aggregated metrics
    await _update_metrics(
        db,
        entity_type=entity_type,
        field_name=field_name,
        is_correction=feedback_type == "correct",
        original_value=original_value,
        corrected_value=corrected_value,
    )

    return feedback


async def _update_metrics(
    db: AsyncSession,
    *,
    entity_type: str,
    field_name: str,
    is_correction: bool,
    original_value: str,
    corrected_value: str,
) -> AIMetrics:
    """Upsert AIMetrics row and recalculate error_rate + common_errors."""
    stmt = select(AIMetrics).where(
        AIMetrics.entity_type == entity_type,
        AIMetrics.field_name == field_name,
    )
    result = await db.execute(stmt)
    metrics = result.scalar_one_or_none()

    if metrics is None:
        metrics = AIMetrics(
            id=uuid.uuid4(),
            entity_type=entity_type,
            field_name=field_name,
            total_extractions=1,
            total_corrections=1 if is_correction else 0,
            error_rate=1.0 if is_correction else 0.0,
            common_errors=[],
        )
        db.add(metrics)
        await db.flush()
    else:
        metrics.total_extractions += 1
        if is_correction:
            metrics.total_corrections += 1

        metrics.error_rate = (
            metrics.total_corrections / metrics.total_extractions if metrics.total_extractions > 0 else 0.0
        )

    # Update common_errors (deep copy to ensure SQLAlchemy detects mutation)
    if is_correction:
        errors = [dict(e) for e in (metrics.common_errors or [])]
        found = False
        for entry in errors:
            if entry.get("original") == original_value and entry.get("corrected") == corrected_value:
                entry["count"] = entry.get("count", 0) + 1
                found = True
                break
        if not found:
            errors.append({"original": original_value, "corrected": corrected_value, "count": 1})
        # Keep top 20 by count
        errors.sort(key=lambda e: e.get("count", 0), reverse=True)
        metrics.common_errors = errors[:20]

    await db.flush()
    return metrics


async def get_metrics(
    db: AsyncSession,
    entity_type: str | None = None,
) -> list[AIMetrics]:
    """Get aggregated metrics, optionally filtered by entity_type."""
    stmt = select(AIMetrics)
    if entity_type:
        stmt = stmt.where(AIMetrics.entity_type == entity_type)
    stmt = stmt.order_by(AIMetrics.entity_type, AIMetrics.field_name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_metrics_summary(
    db: AsyncSession,
    entity_type: str | None = None,
) -> dict:
    """Get dashboard-level summary across all tracked fields."""
    metrics = await get_metrics(db, entity_type=entity_type)
    total_ext = sum(m.total_extractions for m in metrics)
    total_corr = sum(m.total_corrections for m in metrics)
    overall_accuracy = 1.0 - (total_corr / total_ext) if total_ext > 0 else 1.0
    return {
        "overall_accuracy": round(overall_accuracy, 4),
        "total_extractions": total_ext,
        "total_corrections": total_corr,
        "metrics": metrics,
    }


async def list_feedback(
    db: AsyncSession,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    limit: int = 50,
) -> list[AIFeedback]:
    """List feedback records with optional filters."""
    stmt = select(AIFeedback).order_by(AIFeedback.created_at.desc()).limit(limit)
    if entity_type:
        stmt = stmt.where(AIFeedback.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AIFeedback.entity_id == entity_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
