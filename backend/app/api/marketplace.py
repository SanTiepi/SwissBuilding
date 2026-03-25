"""BatiConnect — Marketplace API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.marketplace import (
    CompanyProfileCreate,
    CompanyProfileRead,
    CompanyProfileUpdate,
    CompanySubscriptionCreate,
    CompanySubscriptionRead,
    CompanySubscriptionUpdate,
    CompanyVerificationRead,
    NetworkEligibilityCheck,
    VerificationDecision,
)
from app.services.marketplace_service import (
    check_network_eligibility,
    create_company_profile,
    create_subscription,
    get_company_profile,
    get_subscription,
    get_subscription_by_id,
    get_verification,
    list_company_profiles,
    list_eligible_companies,
    list_verification_queue,
    review_verification,
    submit_for_verification,
    update_company_profile,
    update_subscription_status,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Company Profiles
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/companies",
    response_model=CompanyProfileRead,
    status_code=201,
)
async def create_company_endpoint(
    payload: CompanyProfileCreate,
    current_user: User = Depends(require_permission("organizations", "create")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    profile = await create_company_profile(db, data)
    await db.commit()
    return profile


@router.get(
    "/marketplace/companies",
    response_model=PaginatedResponse[CompanyProfileRead],
)
async def list_companies_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    canton: str | None = None,
    work_category: str | None = None,
    verified_only: bool = False,
    current_user: User = Depends(require_permission("organizations", "list")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_company_profiles(
        db, canton=canton, work_category=work_category, verified_only=verified_only, page=page, size=size
    )
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get(
    "/marketplace/companies/eligible",
    response_model=PaginatedResponse[CompanyProfileRead],
)
async def list_eligible_companies_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("organizations", "list")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_eligible_companies(db, page=page, size=size)
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get(
    "/marketplace/companies/{profile_id}",
    response_model=CompanyProfileRead,
)
async def get_company_endpoint(
    profile_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_company_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return profile


@router.put(
    "/marketplace/companies/{profile_id}",
    response_model=CompanyProfileRead,
)
async def update_company_endpoint(
    profile_id: UUID,
    payload: CompanyProfileUpdate,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_company_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    data = payload.model_dump(exclude_unset=True)
    updated = await update_company_profile(db, profile, data)
    await db.commit()
    return updated


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/companies/{profile_id}/verify",
    response_model=CompanyVerificationRead,
    status_code=201,
)
async def submit_verification_endpoint(
    profile_id: UUID,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_company_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    verification = await submit_for_verification(db, profile_id)
    await db.commit()
    return verification


@router.get(
    "/marketplace/verifications/queue",
    response_model=list[CompanyVerificationRead],
)
async def verification_queue_endpoint(
    current_user: User = Depends(require_permission("organizations", "list")),
    db: AsyncSession = Depends(get_db),
):
    return await list_verification_queue(db)


@router.post(
    "/marketplace/verifications/{verification_id}/decide",
    response_model=CompanyVerificationRead,
)
async def decide_verification_endpoint(
    verification_id: UUID,
    payload: VerificationDecision,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    verification = await get_verification(db, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    if payload.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")
    decision = payload.model_dump()
    updated = await review_verification(db, verification, decision, current_user.id)
    await db.commit()
    return updated


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/companies/{profile_id}/eligibility",
    response_model=NetworkEligibilityCheck,
)
async def check_eligibility_endpoint(
    profile_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_company_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    result = await check_network_eligibility(db, profile_id)
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/companies/{profile_id}/subscription",
    response_model=CompanySubscriptionRead,
    status_code=201,
)
async def create_subscription_endpoint(
    profile_id: UUID,
    payload: CompanySubscriptionCreate,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_company_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    data = payload.model_dump()
    sub = await create_subscription(db, profile_id, data)
    await db.commit()
    return sub


@router.get(
    "/marketplace/companies/{profile_id}/subscription",
    response_model=CompanySubscriptionRead,
)
async def get_subscription_endpoint(
    profile_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_subscription(db, profile_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


@router.put(
    "/marketplace/subscriptions/{subscription_id}",
    response_model=CompanySubscriptionRead,
)
async def update_subscription_endpoint(
    subscription_id: UUID,
    payload: CompanySubscriptionUpdate,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_subscription_by_id(db, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    data = payload.model_dump(exclude_unset=True)
    updated = await update_subscription_status(db, sub, data)
    await db.commit()
    return updated
