"""BatiConnect — Remediation workspace read-model service."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.award_confirmation import AwardConfirmation
from app.models.client_request import ClientRequest
from app.models.company_profile import CompanyProfile
from app.models.company_subscription import CompanySubscription
from app.models.company_verification import CompanyVerification
from app.models.completion_confirmation import CompletionConfirmation
from app.models.post_works_link import PostWorksLink
from app.models.quote import Quote
from app.models.request_invitation import RequestInvitation
from app.models.review import Review
from app.schemas.growth_stack import (
    CompanyWorkspaceSummary,
    CompletionClosureSummary,
    OperatorRemediationQueue,
    QuoteComparisonMatrix,
    QuoteComparisonRow,
)


async def get_company_workspace(db: AsyncSession, company_profile_id: uuid.UUID) -> CompanyWorkspaceSummary | None:
    """Build a company workspace summary from live counts."""
    result = await db.execute(select(CompanyProfile).where(CompanyProfile.id == company_profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        return None

    # Verification
    verif = await db.execute(
        select(func.count())
        .select_from(CompanyVerification)
        .where(CompanyVerification.company_profile_id == company_profile_id)
        .where(CompanyVerification.status == "approved")
    )
    is_verified = (verif.scalar() or 0) > 0

    # Subscription
    sub_result = await db.execute(
        select(CompanySubscription).where(CompanySubscription.company_profile_id == company_profile_id)
    )
    sub = sub_result.scalar_one_or_none()

    # Pending invitations
    inv_count = (
        await db.execute(
            select(func.count())
            .select_from(RequestInvitation)
            .where(RequestInvitation.company_profile_id == company_profile_id)
            .where(RequestInvitation.status == "pending")
        )
    ).scalar() or 0

    # Active RFQs (invitations that are accepted → linked requests still open)
    active_rfqs = (
        await db.execute(
            select(func.count())
            .select_from(RequestInvitation)
            .where(RequestInvitation.company_profile_id == company_profile_id)
            .where(RequestInvitation.status.in_(["accepted", "viewed"]))
        )
    ).scalar() or 0

    # Draft quotes
    draft_quotes = (
        await db.execute(
            select(func.count())
            .select_from(Quote)
            .where(Quote.company_profile_id == company_profile_id)
            .where(Quote.status == "draft")
        )
    ).scalar() or 0

    # Awards won
    awards = (
        await db.execute(
            select(func.count())
            .select_from(AwardConfirmation)
            .where(AwardConfirmation.company_profile_id == company_profile_id)
        )
    ).scalar() or 0

    # Completions pending
    completions_pending = (
        await db.execute(
            select(func.count())
            .select_from(CompletionConfirmation)
            .join(AwardConfirmation)
            .where(AwardConfirmation.company_profile_id == company_profile_id)
            .where(CompletionConfirmation.status == "pending")
        )
    ).scalar() or 0

    # Reviews published
    reviews_pub = (
        await db.execute(
            select(func.count())
            .select_from(Review)
            .where(Review.company_profile_id == company_profile_id)
            .where(Review.status == "published")
        )
    ).scalar() or 0

    return CompanyWorkspaceSummary(
        company_profile_id=company_profile_id,
        company_name=profile.company_name,
        is_verified=is_verified,
        subscription_status=sub.status if sub else None,
        subscription_plan=sub.plan_type if sub else None,
        pending_invitations=inv_count,
        active_rfqs=active_rfqs,
        draft_quotes=draft_quotes,
        awards_won=awards,
        completions_pending=completions_pending,
        reviews_published=reviews_pub,
    )


async def get_operator_queue(
    db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID | None = None
) -> OperatorRemediationQueue:
    """Build an operator queue from live counts."""
    # Active RFQs created by this user
    active_rfqs = (
        await db.execute(
            select(func.count())
            .select_from(ClientRequest)
            .where(ClientRequest.requester_user_id == user_id)
            .where(ClientRequest.status.in_(["published", "draft"]))
        )
    ).scalar() or 0

    # Quotes received on user's requests
    quotes_received = (
        await db.execute(
            select(func.count())
            .select_from(Quote)
            .join(ClientRequest)
            .where(ClientRequest.requester_user_id == user_id)
            .where(Quote.status == "submitted")
        )
    ).scalar() or 0

    # Awards pending (awarded but not yet completion-confirmed)
    awards_pending = (
        await db.execute(
            select(func.count())
            .select_from(AwardConfirmation)
            .join(ClientRequest)
            .where(ClientRequest.requester_user_id == user_id)
            .outerjoin(CompletionConfirmation)
            .where((CompletionConfirmation.id.is_(None)) | (CompletionConfirmation.status == "pending"))
        )
    ).scalar() or 0

    # Completions awaiting
    completions = (
        await db.execute(
            select(func.count())
            .select_from(CompletionConfirmation)
            .join(AwardConfirmation)
            .join(ClientRequest)
            .where(ClientRequest.requester_user_id == user_id)
            .where(CompletionConfirmation.status.in_(["pending", "client_confirmed"]))
        )
    ).scalar() or 0

    # Post-works open
    post_works = (
        await db.execute(
            select(func.count()).select_from(PostWorksLink).where(PostWorksLink.status.in_(["pending", "drafted"]))
        )
    ).scalar() or 0

    return OperatorRemediationQueue(
        active_rfqs=active_rfqs,
        quotes_received=quotes_received,
        awards_pending=awards_pending,
        completions_awaiting=completions,
        post_works_open=post_works,
    )


async def get_quote_comparison_matrix(db: AsyncSession, request_id: uuid.UUID) -> QuoteComparisonMatrix:
    """Build a neutral comparison matrix for quotes on a request, sorted by submitted_at."""
    result = await db.execute(
        select(Quote)
        .where(Quote.client_request_id == request_id)
        .where(Quote.status == "submitted")
        .order_by(Quote.submitted_at)
    )
    quotes = list(result.scalars().all())

    rows: list[QuoteComparisonRow] = []
    for q in quotes:
        # Fetch company name
        cp_result = await db.execute(
            select(CompanyProfile.company_name).where(CompanyProfile.id == q.company_profile_id)
        )
        company_name = cp_result.scalar() or "Unknown"

        rows.append(
            QuoteComparisonRow(
                company_name=company_name,
                amount_chf=float(q.amount_chf) if q.amount_chf else None,
                timeline_weeks=q.timeline_weeks,
                scope_items=q.includes or [],
                exclusions=q.excludes or [],
                confidence=None,  # Populated if AI extraction exists
                ambiguous_fields=[],
                submitted_at=q.submitted_at,
            )
        )

    return QuoteComparisonMatrix(request_id=request_id, rows=rows)


async def get_completion_closure_summary(db: AsyncSession, completion_id: uuid.UUID) -> CompletionClosureSummary | None:
    """Build a closure summary for a completion confirmation."""
    result = await db.execute(select(CompletionConfirmation).where(CompletionConfirmation.id == completion_id))
    cc = result.scalar_one_or_none()
    if cc is None:
        return None

    # Post-works link
    pw_result = await db.execute(select(PostWorksLink).where(PostWorksLink.completion_confirmation_id == completion_id))
    pw = pw_result.scalar_one_or_none()

    # Review
    rev_result = await db.execute(select(Review).where(Review.completion_confirmation_id == completion_id).limit(1))
    rev = rev_result.scalar_one_or_none()

    # Intervention from post-works link
    intervention_id = pw.intervention_id if pw else None

    return CompletionClosureSummary(
        completion_id=completion_id,
        completion_status=cc.status,
        intervention_id=intervention_id,
        post_works_link_status=pw.status if pw else None,
        review_status=rev.status if rev else None,
    )
