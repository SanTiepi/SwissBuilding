"""BatiConnect — Lot 4: Domain Event Projector.

Simple handler registry: event_type → list[async handler_fn(db, event)].
Supports replay of all events for a given aggregate.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_event import DomainEvent

logger = logging.getLogger(__name__)

# Type for async handler: (db, event) -> None
HandlerFn = Callable[[AsyncSession, DomainEvent], Coroutine[Any, Any, None]]

# Global handler registry
_handlers: dict[str, list[HandlerFn]] = defaultdict(list)


def register_handler(event_type: str, handler: HandlerFn) -> None:
    """Register a handler for a domain event type."""
    _handlers[event_type].append(handler)
    logger.debug("Registered handler %s for event_type=%s", handler.__name__, event_type)


async def project_event(db: AsyncSession, event: DomainEvent) -> int:
    """Call all registered handlers for an event. Returns count of handlers invoked."""
    handlers = _handlers.get(event.event_type, [])
    if not handlers:
        logger.debug("No handlers for event_type=%s", event.event_type)
        return 0

    count = 0
    for handler in handlers:
        try:
            await handler(db, event)
            count += 1
        except Exception:
            logger.exception(
                "Handler %s failed for event %s (type=%s)",
                handler.__name__,
                event.id,
                event.event_type,
            )
    return count


async def replay_events(
    db: AsyncSession,
    aggregate_type: str,
    aggregate_id: UUID,
) -> int:
    """Replay all domain events for an aggregate in chronological order.

    Returns total number of handler invocations.
    """
    stmt = (
        select(DomainEvent)
        .where(
            DomainEvent.aggregate_type == aggregate_type,
            DomainEvent.aggregate_id == aggregate_id,
        )
        .order_by(DomainEvent.occurred_at.asc())
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    total = 0
    for event in events:
        total += await project_event(db, event)

    logger.info(
        "Replayed %d events for %s/%s — %d handler invocations",
        len(events),
        aggregate_type,
        aggregate_id,
        total,
    )
    return total


# ---------------------------------------------------------------------------
# Built-in handlers for remediation_post_works_finalized
# ---------------------------------------------------------------------------


async def _handle_post_works_finalized(db: AsyncSession, event: DomainEvent) -> None:
    """Placeholder: refresh passport/trust/readiness for the building.

    In a full implementation this would call passport_service, trust_score_calculator,
    and readiness_reasoner. For now we log the event.
    """
    payload = event.payload or {}
    logger.info(
        "Post-works finalized projection: intervention=%s, verification_rate=%s",
        payload.get("intervention_id"),
        payload.get("verification_rate"),
    )


async def _handle_post_works_finalized_pattern(db: AsyncSession, event: DomainEvent) -> None:
    """Create remediation_outcome pattern from finalized post-works."""
    from app.models.ai_rule_pattern import AIRulePattern

    payload = event.payload or {}
    intervention_id = payload.get("intervention_id")
    if not intervention_id:
        return

    import uuid as _uuid
    from datetime import UTC, datetime

    rule_key = f"remediation_outcome:{intervention_id}"
    pattern = AIRulePattern(
        id=_uuid.uuid4(),
        pattern_type="remediation_outcome",
        source_entity_type="post_works_link",
        rule_key=rule_key,
        rule_definition={
            "intervention_id": str(intervention_id),
            "verification_rate": payload.get("verification_rate"),
        },
        sample_count=1,
        last_confirmed_at=datetime.now(UTC),
        is_active=True,
    )
    db.add(pattern)
    await db.flush()
    logger.info("Created remediation_outcome pattern for intervention=%s", intervention_id)


async def _handle_ai_feedback_recorded(db: AsyncSession, event: DomainEvent) -> None:
    """On ai_feedback_recorded, call pattern_learning_service.record_pattern."""
    payload = event.payload or {}
    feedback_id = payload.get("feedback_id")
    if not feedback_id:
        return

    import uuid as _uuid

    from app.services.pattern_learning_service import record_pattern

    try:
        fid = _uuid.UUID(str(feedback_id))
        pattern = await record_pattern(db, fid)
        if pattern:
            logger.info("Pattern learning recorded for feedback=%s, pattern=%s", feedback_id, pattern.rule_key)
    except Exception:
        logger.exception("Pattern learning failed for feedback=%s", feedback_id)


# Register built-in handlers
register_handler("remediation_post_works_finalized", _handle_post_works_finalized)
register_handler("remediation_post_works_finalized", _handle_post_works_finalized_pattern)
register_handler("ai_feedback_recorded", _handle_ai_feedback_recorded)
