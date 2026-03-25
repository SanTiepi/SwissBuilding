"""BatiConnect — Marketplace service (CompanyProfile, Verification, Subscription)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_profile import CompanyProfile
from app.models.company_subscription import CompanySubscription
from app.models.company_verification import CompanyVerification

# ---------------------------------------------------------------------------
# Profile completeness
# ---------------------------------------------------------------------------

_COMPLETENESS_FIELDS = [
    ("company_name", 0.10),
    ("legal_form", 0.05),
    ("uid_number", 0.05),
    ("address", 0.05),
    ("city", 0.05),
    ("postal_code", 0.03),
    ("canton", 0.02),
    ("contact_email", 0.10),
    ("contact_phone", 0.05),
    ("website", 0.05),
    ("description", 0.10),
    ("work_categories", 0.10),
    ("certifications", 0.10),
    ("regions_served", 0.05),
    ("employee_count", 0.03),
    ("years_experience", 0.03),
    ("insurance_info", 0.04),
]


def compute_profile_completeness(profile: CompanyProfile) -> float:
    """Pure function: compute completeness score 0.0-1.0 from filled fields."""
    score = 0.0
    for field, weight in _COMPLETENESS_FIELDS:
        value = getattr(profile, field, None)
        if value is not None:
            # Lists/dicts must be non-empty to count
            if isinstance(value, (list, dict)) and len(value) == 0:
                continue
            # Empty strings don't count
            if isinstance(value, str) and not value.strip():
                continue
            score += weight
    return round(min(score, 1.0), 2)


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------


async def create_company_profile(db: AsyncSession, data: dict) -> CompanyProfile:
    profile = CompanyProfile(**data)
    profile.profile_completeness = compute_profile_completeness(profile)
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


async def update_company_profile(db: AsyncSession, profile: CompanyProfile, data: dict) -> CompanyProfile:
    for key, value in data.items():
        setattr(profile, key, value)
    profile.profile_completeness = compute_profile_completeness(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


async def get_company_profile(db: AsyncSession, profile_id: UUID) -> CompanyProfile | None:
    result = await db.execute(select(CompanyProfile).where(CompanyProfile.id == profile_id))
    return result.scalar_one_or_none()


async def list_company_profiles(
    db: AsyncSession,
    *,
    canton: str | None = None,
    work_category: str | None = None,
    verified_only: bool = False,
    page: int = 1,
    size: int = 20,
) -> tuple[list[CompanyProfile], int]:
    from sqlalchemy import func

    query = select(CompanyProfile).where(CompanyProfile.is_active.is_(True))
    count_query = select(func.count()).select_from(CompanyProfile).where(CompanyProfile.is_active.is_(True))

    if canton:
        query = query.where(CompanyProfile.canton == canton)
        count_query = count_query.where(CompanyProfile.canton == canton)

    if verified_only:
        # Subquery: profiles with at least one approved verification
        approved_ids = (
            select(CompanyVerification.company_profile_id)
            .where(CompanyVerification.status == "approved")
            .distinct()
            .scalar_subquery()
        )
        query = query.where(CompanyProfile.id.in_(approved_ids))
        count_query = count_query.where(CompanyProfile.id.in_(approved_ids))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(CompanyProfile.company_name).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()

    # Post-filter by work_category (JSON array — can't do portably in SQLite + PG)
    if work_category and items:
        items = [p for p in items if work_category in (p.work_categories or [])]
        total = len(items)

    return list(items), total


async def list_eligible_companies(
    db: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
) -> tuple[list[CompanyProfile], int]:
    """Return only companies that are verified + have active subscription."""
    from sqlalchemy import func

    approved_ids = (
        select(CompanyVerification.company_profile_id)
        .where(CompanyVerification.status == "approved")
        .distinct()
        .scalar_subquery()
    )
    active_sub_ids = (
        select(CompanySubscription.company_profile_id)
        .where(CompanySubscription.status == "active")
        .distinct()
        .scalar_subquery()
    )

    base = (
        select(CompanyProfile)
        .where(CompanyProfile.is_active.is_(True))
        .where(CompanyProfile.id.in_(approved_ids))
        .where(CompanyProfile.id.in_(active_sub_ids))
    )
    count_base = (
        select(func.count())
        .select_from(CompanyProfile)
        .where(CompanyProfile.is_active.is_(True))
        .where(CompanyProfile.id.in_(approved_ids))
        .where(CompanyProfile.id.in_(active_sub_ids))
    )

    total = (await db.execute(count_base)).scalar() or 0
    query = base.order_by(CompanyProfile.company_name).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


async def submit_for_verification(
    db: AsyncSession, profile_id: UUID, verification_type: str = "initial"
) -> CompanyVerification:
    verification = CompanyVerification(
        company_profile_id=profile_id,
        status="pending",
        verification_type=verification_type,
    )
    db.add(verification)
    await db.flush()
    await db.refresh(verification)
    return verification


async def get_verification(db: AsyncSession, verification_id: UUID) -> CompanyVerification | None:
    result = await db.execute(select(CompanyVerification).where(CompanyVerification.id == verification_id))
    return result.scalar_one_or_none()


async def review_verification(
    db: AsyncSession,
    verification: CompanyVerification,
    decision: dict,
    reviewer_id: UUID,
) -> CompanyVerification:
    verification.status = decision["status"]
    verification.verified_by_user_id = reviewer_id
    verification.verified_at = datetime.now(UTC)
    verification.checks_performed = decision.get("checks_performed")
    verification.rejection_reason = decision.get("rejection_reason")
    verification.valid_until = decision.get("valid_until")
    verification.notes = decision.get("notes")
    await db.flush()
    await db.refresh(verification)
    return verification


async def list_verification_queue(db: AsyncSession) -> list[CompanyVerification]:
    result = await db.execute(
        select(CompanyVerification)
        .where(CompanyVerification.status.in_(["pending", "in_review"]))
        .order_by(CompanyVerification.created_at)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Network eligibility
# ---------------------------------------------------------------------------


async def check_network_eligibility(db: AsyncSession, profile_id: UUID) -> dict:
    """Check if a company is eligible for the network (verified + active subscription)."""
    # Check verification
    verif_result = await db.execute(
        select(CompanyVerification)
        .where(CompanyVerification.company_profile_id == profile_id)
        .where(CompanyVerification.status == "approved")
        .limit(1)
    )
    verification = verif_result.scalar_one_or_none()
    is_verified = verification is not None

    # Check subscription
    sub_result = await db.execute(
        select(CompanySubscription).where(CompanySubscription.company_profile_id == profile_id).limit(1)
    )
    subscription = sub_result.scalar_one_or_none()
    has_active_sub = subscription is not None and subscription.status == "active"

    is_eligible = is_verified and has_active_sub

    # Update subscription flag if it exists
    if subscription:
        subscription.is_network_eligible = is_eligible
        await db.flush()

    return {
        "company_profile_id": str(profile_id),
        "is_eligible": is_eligible,
        "is_verified": is_verified,
        "has_active_subscription": has_active_sub,
        "verification_status": verification.status if verification else None,
        "subscription_status": subscription.status if subscription else None,
    }


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


async def create_subscription(db: AsyncSession, profile_id: UUID, data: dict) -> CompanySubscription:
    sub = CompanySubscription(company_profile_id=profile_id, **data)
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def get_subscription(db: AsyncSession, profile_id: UUID) -> CompanySubscription | None:
    result = await db.execute(select(CompanySubscription).where(CompanySubscription.company_profile_id == profile_id))
    return result.scalar_one_or_none()


async def get_subscription_by_id(db: AsyncSession, subscription_id: UUID) -> CompanySubscription | None:
    result = await db.execute(select(CompanySubscription).where(CompanySubscription.id == subscription_id))
    return result.scalar_one_or_none()


async def update_subscription_status(
    db: AsyncSession, subscription: CompanySubscription, data: dict
) -> CompanySubscription:
    for key, value in data.items():
        setattr(subscription, key, value)
    await db.flush()
    await db.refresh(subscription)
    return subscription


# ---------------------------------------------------------------------------
# Subscription lifecycle (Growth Stack)
# ---------------------------------------------------------------------------


async def change_subscription_plan(
    db: AsyncSession,
    subscription_id: UUID,
    new_plan: str,
    user_id: UUID | None = None,
    reason: str | None = None,
) -> CompanySubscription:
    from app.models.subscription_change import SubscriptionChange

    sub = await get_subscription_by_id(db, subscription_id)
    if sub is None:
        raise ValueError("Subscription not found")

    old_plan = sub.plan_type
    sub.plan_type = new_plan

    change = SubscriptionChange(
        subscription_id=subscription_id,
        change_type="plan_changed",
        old_plan=old_plan,
        new_plan=new_plan,
        changed_by_user_id=user_id,
        reason=reason,
    )
    db.add(change)
    await db.flush()
    await db.refresh(sub)
    return sub


async def suspend_subscription(
    db: AsyncSession,
    subscription_id: UUID,
    user_id: UUID | None = None,
    reason: str | None = None,
) -> CompanySubscription:
    from app.models.subscription_change import SubscriptionChange

    sub = await get_subscription_by_id(db, subscription_id)
    if sub is None:
        raise ValueError("Subscription not found")

    old_status = sub.status
    sub.status = "suspended"

    change = SubscriptionChange(
        subscription_id=subscription_id,
        change_type="suspended",
        old_plan=sub.plan_type,
        new_plan=sub.plan_type,
        changed_by_user_id=user_id,
        reason=reason or f"Suspended from {old_status}",
    )
    db.add(change)
    await db.flush()
    await db.refresh(sub)
    return sub


async def reactivate_subscription(
    db: AsyncSession,
    subscription_id: UUID,
    user_id: UUID | None = None,
) -> CompanySubscription:
    from app.models.subscription_change import SubscriptionChange

    sub = await get_subscription_by_id(db, subscription_id)
    if sub is None:
        raise ValueError("Subscription not found")

    sub.status = "active"

    change = SubscriptionChange(
        subscription_id=subscription_id,
        change_type="reactivated",
        old_plan=sub.plan_type,
        new_plan=sub.plan_type,
        changed_by_user_id=user_id,
    )
    db.add(change)
    await db.flush()
    await db.refresh(sub)
    return sub


async def get_subscription_history(db: AsyncSession, profile_id: UUID) -> list:
    """Return all subscription changes for a company profile's subscription."""
    from app.models.subscription_change import SubscriptionChange

    sub = await get_subscription(db, profile_id)
    if sub is None:
        return []

    result = await db.execute(
        select(SubscriptionChange)
        .where(SubscriptionChange.subscription_id == sub.id)
        .order_by(SubscriptionChange.created_at.desc())
    )
    return list(result.scalars().all())


async def get_eligibility_summary(db: AsyncSession, profile_id: UUID) -> dict:
    """Return structured eligibility summary with blockers."""
    verif_result = await db.execute(
        select(CompanyVerification)
        .where(CompanyVerification.company_profile_id == profile_id)
        .where(CompanyVerification.status == "approved")
        .limit(1)
    )
    is_verified = verif_result.scalar_one_or_none() is not None

    sub_result = await db.execute(
        select(CompanySubscription).where(CompanySubscription.company_profile_id == profile_id).limit(1)
    )
    subscription = sub_result.scalar_one_or_none()
    sub_active = subscription is not None and subscription.status == "active"

    blockers: list[str] = []
    if not is_verified:
        blockers.append("company_not_verified")
    if not sub_active:
        blockers.append("no_active_subscription")

    return {
        "company_profile_id": profile_id,
        "verified": is_verified,
        "subscription_active": sub_active,
        "eligible": is_verified and sub_active,
        "blockers": blockers,
    }
