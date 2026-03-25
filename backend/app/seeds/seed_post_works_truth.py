"""BatiConnect — Lot 4: Seed data for PostWorksLink, DomainEvent, AIFeedback.

Depends on marketplace trust seeds (award_confirmation, completion_confirmation).
Idempotent: checks for existing records before inserting.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_feedback import AIFeedback
from app.models.domain_event import DomainEvent
from app.models.post_works_link import PostWorksLink

logger = logging.getLogger(__name__)

# Deterministic UUIDs for seed data
SEED_PWL_ID = UUID("a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e400")
SEED_EVENT_1 = UUID("a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e401")
SEED_EVENT_2 = UUID("a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e402")
SEED_EVENT_3 = UUID("a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e403")
SEED_FB_1 = UUID("a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e404")
SEED_FB_2 = UUID("a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e405")


async def seed_post_works_truth(
    db: AsyncSession,
    *,
    completion_confirmation_id: UUID | None = None,
    intervention_id: UUID | None = None,
    user_id: UUID | None = None,
) -> dict:
    """Seed PostWorksLink, DomainEvents, and AIFeedback records.

    Returns dict with counts of created records.
    """
    created = {"post_works_links": 0, "domain_events": 0, "ai_feedback": 0}

    # Use placeholder UUIDs if not provided
    cc_id = completion_confirmation_id or uuid4()
    int_id = intervention_id or uuid4()
    uid = user_id or uuid4()

    # --- PostWorksLink ---
    existing = await db.get(PostWorksLink, SEED_PWL_ID)
    if existing is None:
        link = PostWorksLink(
            id=SEED_PWL_ID,
            completion_confirmation_id=cc_id,
            intervention_id=int_id,
            status="finalized",
            grade_delta={"before": "C", "after": "B", "change": "+1"},
            trust_delta={"before": 0.52, "after": 0.78, "change": 0.26},
            completeness_delta={"before": 0.65, "after": 0.82, "change": 0.17},
            residual_risks=[
                {
                    "risk_type": "asbestos",
                    "description": "Remaining encapsulated material in basement",
                    "severity": "low",
                },
            ],
            drafted_at=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
            finalized_at=datetime(2026, 3, 22, 14, 30, tzinfo=UTC),
            reviewed_by_user_id=uid,
            reviewed_at=datetime(2026, 3, 21, 9, 0, tzinfo=UTC),
        )
        db.add(link)
        created["post_works_links"] += 1

    # --- DomainEvents ---
    events_data = [
        (
            SEED_EVENT_1,
            "remediation_award_linked",
            "intervention",
            int_id,
            {
                "award_confirmation_id": str(uuid4()),
                "intervention_id": str(int_id),
            },
        ),
        (
            SEED_EVENT_2,
            "remediation_completion_fully_confirmed",
            "completion",
            cc_id,
            {
                "completion_confirmation_id": str(cc_id),
            },
        ),
        (
            SEED_EVENT_3,
            "remediation_post_works_finalized",
            "post_works_link",
            SEED_PWL_ID,
            {
                "intervention_id": str(int_id),
                "verification_rate": 0.85,
                "residual_risk_count": 1,
                "grade_delta": {"before": "C", "after": "B", "change": "+1"},
            },
        ),
    ]
    for evt_id, evt_type, agg_type, agg_id, payload in events_data:
        existing_evt = await db.get(DomainEvent, evt_id)
        if existing_evt is None:
            evt = DomainEvent(
                id=evt_id,
                event_type=evt_type,
                aggregate_type=agg_type,
                aggregate_id=agg_id,
                payload=payload,
                actor_user_id=uid,
                occurred_at=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
            )
            db.add(evt)
            created["domain_events"] += 1

    # --- AIFeedback ---
    feedbacks_data = [
        (SEED_FB_1, "confirm", "post_works_state", uuid4(), None, None, "gpt-4o", 0.92, None),
        (
            SEED_FB_2,
            "correct",
            "post_works_state",
            uuid4(),
            {"state_type": "removed", "pollutant": "asbestos"},
            {"state_type": "encapsulated", "pollutant": "asbestos"},
            "gpt-4o",
            0.78,
            "State was encapsulated, not fully removed",
        ),
    ]
    for fb_id, fb_type, ent_type, ent_id, original, corrected, model, conf, notes in feedbacks_data:
        existing_fb = await db.get(AIFeedback, fb_id)
        if existing_fb is None:
            fb = AIFeedback(
                id=fb_id,
                feedback_type=fb_type,
                entity_type=ent_type,
                entity_id=ent_id,
                original_output=original,
                corrected_output=corrected,
                ai_model=model,
                confidence=conf,
                user_id=uid,
                notes=notes,
            )
            db.add(fb)
            created["ai_feedback"] += 1

    await db.flush()
    logger.info("Seeded post-works truth: %s", created)
    return created
