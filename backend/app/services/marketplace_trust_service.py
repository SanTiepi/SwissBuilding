"""BatiConnect — Marketplace Trust service (Award, Completion, Review, Building linkage)."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.award_confirmation import AwardConfirmation
from app.models.client_request import ClientRequest
from app.models.completion_confirmation import CompletionConfirmation
from app.models.quote import Quote
from app.models.review import Review

# ---------------------------------------------------------------------------
# Award
# ---------------------------------------------------------------------------


def _compute_award_hash(award: AwardConfirmation) -> str:
    content = {
        "client_request_id": str(award.client_request_id),
        "quote_id": str(award.quote_id),
        "company_profile_id": str(award.company_profile_id),
        "award_amount_chf": str(award.award_amount_chf) if award.award_amount_chf else None,
        "conditions": award.conditions,
        "awarded_at": award.awarded_at.isoformat() if award.awarded_at else None,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


async def award_quote(
    db: AsyncSession,
    request_id: UUID,
    quote_id: UUID,
    user_id: UUID,
    conditions: str | None = None,
) -> AwardConfirmation:
    """Award a quote: creates AwardConfirmation, updates Quote+ClientRequest status, creates CompletionConfirmation."""
    # Validate quote
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise ValueError("Quote not found")
    if quote.client_request_id != request_id:
        raise ValueError("Quote does not belong to this request")
    if quote.status != "submitted":
        raise ValueError(f"Cannot award quote in status '{quote.status}'")

    # Validate request
    req_result = await db.execute(select(ClientRequest).where(ClientRequest.id == request_id))
    req = req_result.scalar_one_or_none()
    if not req:
        raise ValueError("Request not found")
    if req.status not in ("published", "closed"):
        raise ValueError(f"Cannot award request in status '{req.status}'")

    now = datetime.now(UTC)

    # Create AwardConfirmation
    award = AwardConfirmation(
        client_request_id=request_id,
        quote_id=quote_id,
        company_profile_id=quote.company_profile_id,
        awarded_by_user_id=user_id,
        award_amount_chf=quote.amount_chf,
        conditions=conditions,
        awarded_at=now,
    )
    award.content_hash = _compute_award_hash(award)
    db.add(award)

    # Update Quote status
    quote.status = "awarded"

    # Update ClientRequest status
    req.status = "awarded"

    await db.flush()

    # Create CompletionConfirmation in pending
    completion = CompletionConfirmation(
        award_confirmation_id=award.id,
        status="pending",
    )
    db.add(completion)
    await db.flush()
    await db.refresh(award)
    return award


async def get_award(db: AsyncSession, award_id: UUID) -> AwardConfirmation | None:
    result = await db.execute(select(AwardConfirmation).where(AwardConfirmation.id == award_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Completion Confirmation
# ---------------------------------------------------------------------------


def _compute_completion_hash(completion: CompletionConfirmation) -> str:
    content = {
        "award_confirmation_id": str(completion.award_confirmation_id),
        "client_confirmed": completion.client_confirmed,
        "company_confirmed": completion.company_confirmed,
        "completion_notes": completion.completion_notes,
        "final_amount_chf": str(completion.final_amount_chf) if completion.final_amount_chf else None,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


async def get_completion(db: AsyncSession, completion_id: UUID) -> CompletionConfirmation | None:
    result = await db.execute(select(CompletionConfirmation).where(CompletionConfirmation.id == completion_id))
    return result.scalar_one_or_none()


async def confirm_completion_client(
    db: AsyncSession, completion_id: UUID, user_id: UUID, notes: str | None = None
) -> CompletionConfirmation:
    completion = await get_completion(db, completion_id)
    if not completion:
        raise ValueError("Completion confirmation not found")
    if completion.client_confirmed:
        raise ValueError("Client has already confirmed completion")
    if completion.status == "disputed":
        raise ValueError("Cannot confirm disputed completion")

    now = datetime.now(UTC)
    completion.client_confirmed = True
    completion.client_confirmed_at = now
    completion.client_confirmed_by_user_id = user_id
    if notes:
        completion.completion_notes = notes

    if completion.company_confirmed:
        completion.status = "fully_confirmed"
        completion.content_hash = _compute_completion_hash(completion)
    else:
        completion.status = "client_confirmed"

    await db.flush()
    await db.refresh(completion)
    return completion


async def confirm_completion_company(
    db: AsyncSession, completion_id: UUID, user_id: UUID, notes: str | None = None
) -> CompletionConfirmation:
    completion = await get_completion(db, completion_id)
    if not completion:
        raise ValueError("Completion confirmation not found")
    if completion.company_confirmed:
        raise ValueError("Company has already confirmed completion")
    if completion.status == "disputed":
        raise ValueError("Cannot confirm disputed completion")

    now = datetime.now(UTC)
    completion.company_confirmed = True
    completion.company_confirmed_at = now
    completion.company_confirmed_by_user_id = user_id
    if notes:
        existing = completion.completion_notes or ""
        completion.completion_notes = f"{existing}\n[Company] {notes}".strip() if existing else notes

    if completion.client_confirmed:
        completion.status = "fully_confirmed"
        completion.content_hash = _compute_completion_hash(completion)
    else:
        completion.status = "company_confirmed"

    await db.flush()
    await db.refresh(completion)
    return completion


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


async def submit_review(db: AsyncSession, review_data: dict, reviewer_user_id: UUID) -> Review:
    """Submit a review. ENFORCES: completion must be fully_confirmed."""
    completion_id = review_data["completion_confirmation_id"]
    completion = await get_completion(db, completion_id)
    if not completion:
        raise ValueError("Completion confirmation not found")
    if completion.status != "fully_confirmed":
        raise ValueError("Cannot submit review: completion is not fully confirmed (double confirmation required)")

    now = datetime.now(UTC)
    review = Review(
        **review_data,
        reviewer_user_id=reviewer_user_id,
        status="submitted",
        submitted_at=now,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return review


async def moderate_review(
    db: AsyncSession,
    review_id: UUID,
    moderator_user_id: UUID,
    decision: str,
    notes: str | None = None,
    rejection_reason: str | None = None,
) -> Review:
    """Moderate a review: approve -> published, reject -> rejected."""
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise ValueError("Review not found")
    if review.status not in ("submitted", "under_moderation"):
        raise ValueError(f"Cannot moderate review in status '{review.status}'")

    now = datetime.now(UTC)
    review.moderated_by_user_id = moderator_user_id
    review.moderated_at = now
    review.moderation_notes = notes

    if decision == "approve":
        review.status = "published"
        review.published_at = now
    elif decision == "reject":
        review.status = "rejected"
        review.rejection_reason = rejection_reason or notes
    else:
        raise ValueError(f"Invalid decision: {decision}")

    await db.flush()
    await db.refresh(review)
    return review


async def get_company_reviews(db: AsyncSession, company_profile_id: UUID) -> list[Review]:
    """Get published reviews for a company."""
    result = await db.execute(
        select(Review)
        .where(Review.company_profile_id == company_profile_id)
        .where(Review.status == "published")
        .order_by(Review.published_at.desc())
    )
    return list(result.scalars().all())


async def get_company_rating_summary(db: AsyncSession, company_profile_id: UUID) -> dict:
    """Average rating + breakdown from published reviews only."""
    result = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.avg(Review.rating).label("avg_rating"),
            func.avg(Review.quality_score).label("avg_quality"),
            func.avg(Review.timeliness_score).label("avg_timeliness"),
            func.avg(Review.communication_score).label("avg_communication"),
        )
        .where(Review.company_profile_id == company_profile_id)
        .where(Review.status == "published")
    )
    row = result.one()
    total = row.total or 0

    # Rating breakdown
    breakdown = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    if total > 0:
        breakdown_result = await db.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.company_profile_id == company_profile_id)
            .where(Review.status == "published")
            .group_by(Review.rating)
        )
        for rating, count in breakdown_result.all():
            breakdown[str(rating)] = count

    return {
        "company_profile_id": company_profile_id,
        "average_rating": round(float(row.avg_rating), 2) if row.avg_rating else None,
        "total_reviews": total,
        "rating_breakdown": breakdown,
        "average_quality": round(float(row.avg_quality), 2) if row.avg_quality else None,
        "average_timeliness": round(float(row.avg_timeliness), 2) if row.avg_timeliness else None,
        "average_communication": round(float(row.avg_communication), 2) if row.avg_communication else None,
    }


async def get_pending_reviews(db: AsyncSession) -> list[Review]:
    """Get reviews pending moderation."""
    result = await db.execute(
        select(Review).where(Review.status.in_(["submitted", "under_moderation"])).order_by(Review.submitted_at)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Building Linkage
# ---------------------------------------------------------------------------


async def link_to_building(db: AsyncSession, award_id: UUID) -> dict:
    """Link an award to its building: creates timeline event + evidence refs for post-works."""
    award = await get_award(db, award_id)
    if not award:
        raise ValueError("Award not found")

    # Get the client request to find the building
    req_result = await db.execute(select(ClientRequest).where(ClientRequest.id == award.client_request_id))
    req = req_result.scalar_one_or_none()
    if not req:
        raise ValueError("Client request not found")

    building_id = req.building_id

    # Create timeline event via the existing event model
    from app.models.event import Event

    event_date = (award.awarded_at or datetime.now(UTC)).date()
    event = Event(
        building_id=building_id,
        event_type="marketplace_award",
        date=event_date,
        title=f"Remediation contract awarded — {req.title}",
        description=(
            f"Quote awarded to company (award {award.id}). "
            f"Amount: CHF {award.award_amount_chf}. "
            f"Conditions: {award.conditions or 'None'}"
        ),
        metadata_json={"award_id": str(award.id), "quote_id": str(award.quote_id)},
    )
    db.add(event)

    # Create evidence link
    from app.models.evidence_link import EvidenceLink

    evidence = EvidenceLink(
        source_type="award_confirmation",
        source_id=award.id,
        target_type="building",
        target_id=building_id,
        relationship="remediation_contract",
    )
    db.add(evidence)

    await db.flush()
    await db.refresh(event)

    return {
        "award_id": award_id,
        "building_id": building_id,
        "event_id": event.id,
        "linked_at": datetime.now(UTC).isoformat(),
    }
