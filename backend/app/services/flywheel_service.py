"""Flywheel learning loop — document classification & extraction feedback.

Records human corrections on AI-generated classifications and extractions,
computes accuracy metrics, and discovers learned rules from correction patterns.
Every correction improves the system: more usage -> better accuracy -> less human work.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_feedback import AIFeedback
from app.models.document import Document

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Record feedback
# ---------------------------------------------------------------------------


async def record_classification_feedback(
    db: AsyncSession,
    document_id: UUID,
    predicted_type: str,
    corrected_type: str,
    user_id: UUID,
) -> dict:
    """Store a classification correction and update the document type.

    Returns the feedback record as a dict.
    """
    is_correct = predicted_type == corrected_type
    feedback_type = "confirm" if is_correct else "correct"

    feedback = AIFeedback(
        id=_uuid.uuid4(),
        feedback_type=feedback_type,
        entity_type="classification",
        entity_id=document_id,
        original_output={"document_type": predicted_type},
        corrected_output={"document_type": corrected_type},
        confidence=1.0 if is_correct else None,
        user_id=user_id,
        created_at=datetime.now(UTC),
    )
    db.add(feedback)

    # Update document type with corrected value
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc:
        doc.document_type = corrected_type
        # Mark as human-corrected in metadata
        pm = dict(doc.processing_metadata) if doc.processing_metadata else {}
        pm["classification_feedback"] = {
            "predicted": predicted_type,
            "corrected": corrected_type,
            "feedback_type": feedback_type,
            "corrected_at": datetime.now(UTC).isoformat(),
            "corrected_by": str(user_id),
        }
        doc.processing_metadata = pm

    await db.flush()

    return {
        "id": str(feedback.id),
        "feedback_type": feedback_type,
        "entity_type": "classification",
        "document_id": str(document_id),
        "predicted_type": predicted_type,
        "corrected_type": corrected_type,
        "is_correct": is_correct,
    }


async def record_extraction_feedback(
    db: AsyncSession,
    document_id: UUID,
    field_name: str,
    predicted_value: str,
    corrected_value: str | None,
    accepted: bool,
    user_id: UUID,
) -> dict:
    """Store an extraction correction or confirmation.

    If accepted=True, confirms the extraction as ground truth.
    If accepted=False, stores the correction for learning.
    """
    if accepted:
        feedback_type = "confirm"
        corrected_output = {"field": field_name, "value": predicted_value, "accepted": True}
    else:
        feedback_type = "correct" if corrected_value else "reject"
        corrected_output = {
            "field": field_name,
            "value": corrected_value,
            "accepted": False,
        }

    feedback = AIFeedback(
        id=_uuid.uuid4(),
        feedback_type=feedback_type,
        entity_type="extraction",
        entity_id=document_id,
        original_output={"field": field_name, "value": predicted_value},
        corrected_output=corrected_output,
        confidence=1.0 if accepted else None,
        user_id=user_id,
        created_at=datetime.now(UTC),
    )
    db.add(feedback)
    await db.flush()

    return {
        "id": str(feedback.id),
        "feedback_type": feedback_type,
        "entity_type": "extraction",
        "document_id": str(document_id),
        "field_name": field_name,
        "predicted_value": predicted_value,
        "corrected_value": corrected_value,
        "accepted": accepted,
    }


# ---------------------------------------------------------------------------
# Accuracy metrics
# ---------------------------------------------------------------------------


async def get_classification_accuracy(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> dict:
    """Compute classification accuracy metrics from feedback records."""
    stmt = select(AIFeedback).where(AIFeedback.entity_type == "classification")
    result = await db.execute(stmt)
    feedbacks = list(result.scalars().all())

    if not feedbacks:
        return {
            "overall_accuracy": 0.0,
            "per_type_accuracy": {},
            "confusion_matrix": [],
            "total_predictions": 0,
            "total_corrections": 0,
            "trend": "stable",
        }

    total = len(feedbacks)
    correct = sum(1 for f in feedbacks if f.feedback_type == "confirm")
    overall_accuracy = round(correct / max(total, 1), 3)

    # Per-type accuracy
    type_correct: dict[str, int] = defaultdict(int)
    type_total: dict[str, int] = defaultdict(int)
    confusion_pairs: Counter[tuple[str, str]] = Counter()

    for f in feedbacks:
        orig = (f.original_output or {}).get("document_type", "unknown")
        corr = (f.corrected_output or {}).get("document_type", "unknown")
        type_total[orig] += 1
        if f.feedback_type == "confirm":
            type_correct[orig] += 1
        else:
            confusion_pairs[(orig, corr)] += 1

    per_type: dict[str, dict[str, Any]] = {}
    for dtype, tot in type_total.items():
        per_type[dtype] = {
            "accuracy": round(type_correct.get(dtype, 0) / max(tot, 1), 3),
            "total": tot,
            "correct": type_correct.get(dtype, 0),
        }

    # Top confusion pairs
    confusion = [
        {"predicted": pair[0], "actual": pair[1], "count": count} for pair, count in confusion_pairs.most_common(10)
    ]

    # Trend: compare last 30 days vs previous 30
    now = datetime.now(UTC)
    cutoff_recent = now - timedelta(days=30)
    cutoff_prev = now - timedelta(days=60)

    recent = [f for f in feedbacks if f.created_at and _tz_aware(f.created_at) >= cutoff_recent]
    previous = [f for f in feedbacks if f.created_at and cutoff_prev <= _tz_aware(f.created_at) < cutoff_recent]

    trend = _compute_trend(recent, previous)

    return {
        "overall_accuracy": overall_accuracy,
        "per_type_accuracy": per_type,
        "confusion_matrix": confusion,
        "total_predictions": total,
        "total_corrections": total - correct,
        "trend": trend,
    }


async def get_extraction_accuracy(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> dict:
    """Compute extraction accuracy metrics from feedback records."""
    stmt = select(AIFeedback).where(AIFeedback.entity_type == "extraction")
    result = await db.execute(stmt)
    feedbacks = list(result.scalars().all())

    if not feedbacks:
        return {
            "overall_accuracy": 0.0,
            "per_field_accuracy": {},
            "total_extractions": 0,
            "total_corrections": 0,
            "trend": "stable",
        }

    total = len(feedbacks)
    correct = sum(1 for f in feedbacks if f.feedback_type == "confirm")
    overall_accuracy = round(correct / max(total, 1), 3)

    # Per-field accuracy
    field_correct: dict[str, int] = defaultdict(int)
    field_total: dict[str, int] = defaultdict(int)

    for f in feedbacks:
        field = (f.original_output or {}).get("field", "unknown")
        field_total[field] += 1
        if f.feedback_type == "confirm":
            field_correct[field] += 1

    per_field: dict[str, dict[str, Any]] = {}
    for field, tot in field_total.items():
        per_field[field] = {
            "accuracy": round(field_correct.get(field, 0) / max(tot, 1), 3),
            "total": tot,
            "correct": field_correct.get(field, 0),
        }

    # Trend
    now = datetime.now(UTC)
    cutoff_recent = now - timedelta(days=30)
    cutoff_prev = now - timedelta(days=60)

    recent = [f for f in feedbacks if f.created_at and _tz_aware(f.created_at) >= cutoff_recent]
    previous = [f for f in feedbacks if f.created_at and cutoff_prev <= _tz_aware(f.created_at) < cutoff_recent]

    trend = _compute_trend(recent, previous)

    return {
        "overall_accuracy": overall_accuracy,
        "per_field_accuracy": per_field,
        "total_extractions": total,
        "total_corrections": total - correct,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# Learned rules
# ---------------------------------------------------------------------------

RULE_THRESHOLD = 5  # Min corrections before suggesting a rule


async def get_learning_rules(
    db: AsyncSession,
    document_type: str | None = None,
) -> list[dict]:
    """Analyze corrections to discover repeated patterns (learned rules).

    If type X is corrected to Y more than RULE_THRESHOLD times, suggest a rule.
    """
    stmt = select(AIFeedback).where(
        AIFeedback.entity_type == "classification",
        AIFeedback.feedback_type == "correct",
    )
    result = await db.execute(stmt)
    corrections = list(result.scalars().all())

    # Count (predicted -> corrected) transitions
    transition_counts: Counter[tuple[str, str]] = Counter()
    for f in corrections:
        orig = (f.original_output or {}).get("document_type", "unknown")
        corr = (f.corrected_output or {}).get("document_type", "unknown")
        if document_type and orig != document_type:
            continue
        transition_counts[(orig, corr)] += 1

    rules: list[dict] = []
    for (predicted, actual), count in transition_counts.most_common():
        if count >= RULE_THRESHOLD:
            confidence = round(min(count / (RULE_THRESHOLD * 3), 1.0), 2)
            rules.append(
                {
                    "predicted_type": predicted,
                    "corrected_type": actual,
                    "occurrence_count": count,
                    "confidence": confidence,
                    "suggestion": (
                        f"Documents classified as '{predicted}' are frequently "
                        f"corrected to '{actual}' ({count} times). "
                        f"Consider updating classification rules."
                    ),
                }
            )

    return rules


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


async def get_flywheel_dashboard(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> dict:
    """Aggregate all flywheel metrics into a single dashboard view."""
    classification = await get_classification_accuracy(db, org_id)
    extraction = await get_extraction_accuracy(db, org_id)
    rules = await get_learning_rules(db)

    total_processed = classification["total_predictions"] + extraction["total_extractions"]
    total_corrections = classification["total_corrections"] + extraction["total_corrections"]
    correction_rate = round(total_corrections / max(total_processed, 1), 3)

    # Top confusion pairs from classification
    top_confusion = classification.get("confusion_matrix", [])[:5]

    # Combined trend: prefer classification trend if available
    trend = classification.get("trend", "stable")

    return {
        "classification_accuracy": classification["overall_accuracy"],
        "extraction_accuracy": extraction["overall_accuracy"],
        "total_documents_processed": total_processed,
        "total_corrections": total_corrections,
        "correction_rate": correction_rate,
        "top_confusion_pairs": top_confusion,
        "learned_rules_count": len(rules),
        "learned_rules": rules,
        "improvement_trend": trend,
        "classification_detail": classification,
        "extraction_detail": extraction,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tz_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). SQLite returns naive datetimes."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _compute_trend(
    recent: list[AIFeedback],
    previous: list[AIFeedback],
) -> str:
    """Compare accuracy in two time windows to determine trend."""
    if not recent or not previous:
        return "stable"

    recent_correct = sum(1 for f in recent if f.feedback_type == "confirm")
    recent_acc = recent_correct / max(len(recent), 1)

    prev_correct = sum(1 for f in previous if f.feedback_type == "confirm")
    prev_acc = prev_correct / max(len(previous), 1)

    diff = recent_acc - prev_acc
    if diff > 0.05:
        return "improving"
    elif diff < -0.05:
        return "declining"
    return "stable"
