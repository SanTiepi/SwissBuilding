"""BatiConnect — Pattern Learning service.

Records extraction/correction patterns for future improvement.
Patterns never auto-mutate building truth — they are advisory only.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_feedback import AIFeedback
from app.models.ai_rule_pattern import AIRulePattern

logger = logging.getLogger(__name__)


async def record_pattern(db: AsyncSession, feedback_id: uuid.UUID) -> AIRulePattern | None:
    """After confirmed/corrected feedback, upsert an AIRulePattern.

    Only creates patterns from confirm/correct feedback — rejects are ignored.
    """
    result = await db.execute(select(AIFeedback).where(AIFeedback.id == feedback_id))
    feedback = result.scalar_one_or_none()
    if feedback is None:
        logger.warning("Feedback %s not found for pattern learning", feedback_id)
        return None

    if feedback.feedback_type not in ("confirm", "correct"):
        return None

    # Build pattern key from entity_type + feedback type
    pattern_type = "extraction_rule" if feedback.entity_type == "extraction" else "remediation_outcome"
    source_entity_type = feedback.entity_type
    rule_key = f"{source_entity_type}:{feedback.feedback_type}"

    if feedback.ai_model:
        rule_key = f"{rule_key}:{feedback.ai_model}"

    # Upsert: find existing or create
    stmt = select(AIRulePattern).where(
        AIRulePattern.rule_key == rule_key,
        AIRulePattern.pattern_type == pattern_type,
    )
    existing_result = await db.execute(stmt)
    pattern = existing_result.scalar_one_or_none()

    now = datetime.now(UTC)

    if pattern is not None:
        pattern.sample_count += 1
        pattern.last_confirmed_at = now
        pattern.updated_at = now
        if feedback.corrected_output:
            # Update rule_definition with latest correction info
            existing_def = pattern.rule_definition or {}
            corrections = existing_def.get("corrections", [])
            corrections.append(
                {
                    "feedback_id": str(feedback.id),
                    "corrected_fields": list(feedback.corrected_output.keys()) if feedback.corrected_output else [],
                }
            )
            # Keep last 10 corrections
            existing_def["corrections"] = corrections[-10:]
            pattern.rule_definition = existing_def
    else:
        rule_def = {"confidence_threshold": feedback.confidence or 0.5}
        if feedback.corrected_output:
            rule_def["corrections"] = [
                {
                    "feedback_id": str(feedback.id),
                    "corrected_fields": list(feedback.corrected_output.keys()) if feedback.corrected_output else [],
                }
            ]

        pattern = AIRulePattern(
            id=uuid.uuid4(),
            pattern_type=pattern_type,
            source_entity_type=source_entity_type,
            rule_key=rule_key,
            rule_definition=rule_def,
            sample_count=1,
            last_confirmed_at=now,
            is_active=True,
        )
        db.add(pattern)

    await db.flush()
    return pattern


async def get_patterns(
    db: AsyncSession,
    pattern_type_filter: str | None = None,
) -> list[AIRulePattern]:
    """List active patterns, optionally filtered by type."""
    stmt = select(AIRulePattern).where(AIRulePattern.is_active.is_(True))
    if pattern_type_filter:
        stmt = stmt.where(AIRulePattern.pattern_type == pattern_type_filter)
    stmt = stmt.order_by(AIRulePattern.sample_count.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_pattern_stats(db: AsyncSession) -> dict:
    """Summary: total patterns, by type, avg sample_count."""
    # Total active patterns
    total_result = await db.execute(select(func.count(AIRulePattern.id)).where(AIRulePattern.is_active.is_(True)))
    total = total_result.scalar() or 0

    # By type
    type_result = await db.execute(
        select(AIRulePattern.pattern_type, func.count(AIRulePattern.id))
        .where(AIRulePattern.is_active.is_(True))
        .group_by(AIRulePattern.pattern_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # Avg sample count
    avg_result = await db.execute(select(func.avg(AIRulePattern.sample_count)).where(AIRulePattern.is_active.is_(True)))
    avg_sample = float(avg_result.scalar() or 0.0)

    return {
        "total_patterns": total,
        "by_type": by_type,
        "avg_sample_count": avg_sample,
    }
