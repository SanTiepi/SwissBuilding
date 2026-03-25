"""BatiConnect — Lot 4: Remediation Post-Works Service.

Closed-loop post-works truth: Award→Intervention bridge, draft/review/finalize
lifecycle, AI feedback, and domain event emission.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_feedback import AIFeedback
from app.models.award_confirmation import AwardConfirmation
from app.models.completion_confirmation import CompletionConfirmation
from app.models.domain_event import DomainEvent
from app.models.event import Event
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.post_works_link import PostWorksLink
from app.models.post_works_state import PostWorksState
from app.services.post_works_service import generate_post_works_states

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain event helpers
# ---------------------------------------------------------------------------


async def _emit_event(
    db: AsyncSession,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: dict | None = None,
    actor_user_id: UUID | None = None,
) -> DomainEvent:
    evt = DomainEvent(
        id=uuid4(),
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
        actor_user_id=actor_user_id,
        occurred_at=datetime.now(UTC),
    )
    db.add(evt)
    await db.flush()
    return evt


# ---------------------------------------------------------------------------
# Award → Intervention bridge
# ---------------------------------------------------------------------------


async def award_to_intervention(
    db: AsyncSession,
    award_confirmation_id: UUID,
) -> Intervention:
    """Create or find canonical Intervention linked to an award.

    Idempotent: if an intervention already references this award (via notes
    containing the award ID), the existing one is returned.
    """
    award = await db.get(AwardConfirmation, award_confirmation_id)
    if award is None:
        raise ValueError(f"AwardConfirmation {award_confirmation_id} not found")

    # Load related objects
    stmt_award = (
        select(AwardConfirmation)
        .options(
            selectinload(AwardConfirmation.client_request),
            selectinload(AwardConfirmation.quote),
            selectinload(AwardConfirmation.company_profile),
        )
        .where(AwardConfirmation.id == award_confirmation_id)
    )
    result = await db.execute(stmt_award)
    award = result.scalar_one()

    # Idempotency: check if intervention already exists for this award
    award_ref = f"award:{award_confirmation_id}"
    existing_stmt = select(Intervention).where(
        Intervention.notes.contains(award_ref),
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        logger.info("Intervention already exists for award %s → %s", award_confirmation_id, existing.id)
        return existing

    # Create canonical intervention
    cr = award.client_request
    company = award.company_profile
    intervention = Intervention(
        id=uuid4(),
        building_id=cr.building_id,
        intervention_type="remediation",
        title=f"Remediation — {cr.title}",
        description=f"Awarded via marketplace to {company.company_name if company else 'unknown'}",
        status="planned",
        contractor_name=company.company_name if company else None,
        cost_chf=float(award.award_amount_chf) if award.award_amount_chf else None,
        notes=award_ref,
    )
    db.add(intervention)
    await db.flush()

    await _emit_event(
        db,
        event_type="remediation_award_linked",
        aggregate_type="intervention",
        aggregate_id=intervention.id,
        payload={
            "award_confirmation_id": str(award_confirmation_id),
            "intervention_id": str(intervention.id),
            "building_id": str(cr.building_id),
        },
    )
    logger.info("Created intervention %s from award %s", intervention.id, award_confirmation_id)
    return intervention


# ---------------------------------------------------------------------------
# Draft post-works
# ---------------------------------------------------------------------------


async def draft_post_works(
    db: AsyncSession,
    completion_confirmation_id: UUID,
    user_id: UUID,
) -> PostWorksLink:
    """Create a draft PostWorksLink for a fully-confirmed completion.

    Idempotent: returns existing link if already created.
    """
    completion = await db.get(CompletionConfirmation, completion_confirmation_id)
    if completion is None:
        raise ValueError(f"CompletionConfirmation {completion_confirmation_id} not found")
    if completion.status != "fully_confirmed":
        raise ValueError(f"Completion {completion_confirmation_id} is not fully_confirmed (status={completion.status})")

    # Idempotency check
    existing_stmt = select(PostWorksLink).where(
        PostWorksLink.completion_confirmation_id == completion_confirmation_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        logger.info("PostWorksLink already exists for completion %s", completion_confirmation_id)
        return existing

    # Resolve intervention via award
    award = await db.get(AwardConfirmation, completion.award_confirmation_id)
    if award is None:
        raise ValueError(f"AwardConfirmation {completion.award_confirmation_id} not found for completion")

    # Find or create intervention
    intervention = await award_to_intervention(db, award.id)

    # Capture before_snapshot_id — use building_id as reference if time_machine not available
    cr = award.client_request
    if cr is None:
        stmt_award = (
            select(AwardConfirmation)
            .options(selectinload(AwardConfirmation.client_request))
            .where(AwardConfirmation.id == award.id)
        )
        r = await db.execute(stmt_award)
        award = r.scalar_one()
        cr = award.client_request

    building_id = cr.building_id

    link = PostWorksLink(
        id=uuid4(),
        completion_confirmation_id=completion_confirmation_id,
        intervention_id=intervention.id,
        before_snapshot_id=None,
        status="drafted",
        drafted_at=datetime.now(UTC),
    )
    db.add(link)
    await db.flush()

    # Generate draft PostWorksState records (unverified)
    try:
        # Only generate if intervention is completed
        if intervention.status == "completed":
            await generate_post_works_states(
                db,
                building_id=building_id,
                intervention_id=intervention.id,
                recorded_by=user_id,
            )
    except (ValueError, Exception) as exc:
        logger.warning("Could not generate post-works states: %s", exc)

    await _emit_event(
        db,
        event_type="remediation_post_works_drafted",
        aggregate_type="post_works_link",
        aggregate_id=link.id,
        payload={
            "completion_confirmation_id": str(completion_confirmation_id),
            "intervention_id": str(intervention.id),
            "building_id": str(building_id),
        },
        actor_user_id=user_id,
    )
    logger.info("Drafted PostWorksLink %s for completion %s", link.id, completion_confirmation_id)
    return link


# ---------------------------------------------------------------------------
# Review draft
# ---------------------------------------------------------------------------


async def review_draft(
    db: AsyncSession,
    post_works_link_id: UUID,
    user_id: UUID,
) -> PostWorksLink:
    """Move PostWorksLink from drafted → review_required."""
    link = await db.get(PostWorksLink, post_works_link_id)
    if link is None:
        raise ValueError(f"PostWorksLink {post_works_link_id} not found")
    if link.status != "drafted":
        raise ValueError(f"PostWorksLink {post_works_link_id} is not in drafted status (status={link.status})")

    link.status = "review_required"
    link.reviewed_by_user_id = user_id
    link.reviewed_at = datetime.now(UTC)
    await db.flush()
    logger.info("Reviewed PostWorksLink %s → review_required", post_works_link_id)
    return link


# ---------------------------------------------------------------------------
# Finalize post-works
# ---------------------------------------------------------------------------


async def finalize_post_works(
    db: AsyncSession,
    post_works_link_id: UUID,
    user_id: UUID,
) -> PostWorksLink:
    """Finalize a reviewed PostWorksLink: compute deltas, emit events, create evidence.

    Idempotent: if already finalized, returns as-is.
    """
    link = await db.get(PostWorksLink, post_works_link_id)
    if link is None:
        raise ValueError(f"PostWorksLink {post_works_link_id} not found")

    if link.status == "finalized":
        logger.info("PostWorksLink %s already finalized", post_works_link_id)
        return link

    if link.status != "review_required":
        raise ValueError(
            f"PostWorksLink {post_works_link_id} must be review_required to finalize (status={link.status})"
        )

    # Compute deltas (simplified — real implementation uses passport/trust services)
    # Count post-works states for this intervention
    pws_stmt = select(PostWorksState).where(
        PostWorksState.intervention_id == link.intervention_id,
    )
    pws_result = await db.execute(pws_stmt)
    pws_list = pws_result.scalars().all()

    verified_count = sum(1 for p in pws_list if p.verified)
    total_count = len(pws_list)

    # Residual risks from unverified / recheck_needed states
    residual_risks = []
    for p in pws_list:
        if p.state_type in ("recheck_needed", "remaining", "unknown_after_intervention") or not p.verified:
            residual_risks.append(
                {
                    "risk_type": p.pollutant_type or "unknown",
                    "description": p.title,
                    "severity": "medium" if p.state_type == "recheck_needed" else "low",
                }
            )

    verification_rate = (verified_count / total_count) if total_count > 0 else 0.0

    link.grade_delta = {"before": "C", "after": "B", "change": "+1"}
    link.trust_delta = {"before": 0.5, "after": 0.5 + verification_rate * 0.3, "change": verification_rate * 0.3}
    link.completeness_delta = {"before": 0.6, "after": 0.6 + verification_rate * 0.2, "change": verification_rate * 0.2}
    link.residual_risks = residual_risks[:10]  # cap
    link.status = "finalized"
    link.finalized_at = datetime.now(UTC)
    await db.flush()

    # Resolve building_id for timeline event
    intervention = await db.get(Intervention, link.intervention_id)
    if intervention is not None:
        building_id = intervention.building_id

        # Create timeline event
        timeline_evt = Event(
            id=uuid4(),
            building_id=building_id,
            event_type="post_works_finalized",
            date=datetime.now(UTC).date(),
            title="Post-works analysis finalized",
            description=f"Remediation outcome finalized (verification rate: {verification_rate:.0%})",
            created_by=user_id,
            metadata_json={
                "post_works_link_id": str(link.id),
                "intervention_id": str(link.intervention_id),
                "residual_risk_count": len(residual_risks),
            },
        )
        db.add(timeline_evt)

        # Create evidence links
        evidence = EvidenceLink(
            id=uuid4(),
            source_type="post_works_link",
            source_id=link.id,
            target_type="intervention",
            target_id=link.intervention_id,
            relationship="post_works_outcome",
            confidence=verification_rate,
            explanation="Post-works closed-loop evidence",
            created_by=user_id,
        )
        db.add(evidence)
        await db.flush()

    await _emit_event(
        db,
        event_type="remediation_post_works_finalized",
        aggregate_type="post_works_link",
        aggregate_id=link.id,
        payload={
            "intervention_id": str(link.intervention_id),
            "verification_rate": verification_rate,
            "residual_risk_count": len(residual_risks),
            "grade_delta": link.grade_delta,
        },
        actor_user_id=user_id,
    )
    logger.info("Finalized PostWorksLink %s", post_works_link_id)
    return link


# ---------------------------------------------------------------------------
# AI Feedback
# ---------------------------------------------------------------------------


async def record_ai_feedback(
    db: AsyncSession,
    feedback_data: dict,
    user_id: UUID,
) -> AIFeedback:
    """Record human feedback on AI output. Storage/provenance only."""
    fb = AIFeedback(
        id=uuid4(),
        feedback_type=feedback_data["feedback_type"],
        entity_type=feedback_data["entity_type"],
        entity_id=feedback_data["entity_id"],
        original_output=feedback_data.get("original_output"),
        corrected_output=feedback_data.get("corrected_output"),
        ai_model=feedback_data.get("ai_model"),
        confidence=feedback_data.get("confidence"),
        user_id=user_id,
        notes=feedback_data.get("notes"),
    )
    db.add(fb)
    await db.flush()

    await _emit_event(
        db,
        event_type="ai_feedback_recorded",
        aggregate_type="ai_feedback",
        aggregate_id=fb.id,
        payload={
            "feedback_type": fb.feedback_type,
            "entity_type": fb.entity_type,
            "entity_id": str(fb.entity_id),
        },
        actor_user_id=user_id,
    )
    logger.info("Recorded AI feedback %s (type=%s)", fb.id, fb.feedback_type)
    return fb


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


async def get_post_works_link(
    db: AsyncSession,
    completion_confirmation_id: UUID,
) -> PostWorksLink | None:
    """Get PostWorksLink by completion_confirmation_id."""
    stmt = select(PostWorksLink).where(
        PostWorksLink.completion_confirmation_id == completion_confirmation_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_building_remediation_outcomes(
    db: AsyncSession,
    building_id: UUID,
) -> list[PostWorksLink]:
    """Get all PostWorksLinks for interventions on a building."""
    stmt = (
        select(PostWorksLink)
        .join(Intervention, PostWorksLink.intervention_id == Intervention.id)
        .where(Intervention.building_id == building_id)
        .order_by(PostWorksLink.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_domain_events(
    db: AsyncSession,
    aggregate_type: str | None = None,
    aggregate_id: UUID | None = None,
    limit: int = 50,
) -> list[DomainEvent]:
    """List domain events, optionally filtered by aggregate."""
    stmt = select(DomainEvent)
    filters = []
    if aggregate_type:
        filters.append(DomainEvent.aggregate_type == aggregate_type)
    if aggregate_id:
        filters.append(DomainEvent.aggregate_id == aggregate_id)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.order_by(DomainEvent.occurred_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
