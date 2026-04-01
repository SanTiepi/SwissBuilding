"""BatiConnect — Partner trust API routes.

V3 doctrine: trust signals are building-rooted via BuildingCase.
Trust is observational, not ranking. No payment influence (invariant #6).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.partner_trust import (
    CasePartnerTrustRead,
    PartnerTrustProfileRead,
    PartnerTrustSignalRead,
    RoutingHintRead,
    TrustedPartnerRead,
    TrustSignalCreate,
)
from app.services.partner_trust_service import (
    evaluate_partner,
    get_partner_trust_for_case,
    get_profile,
    get_routing_hint,
    get_trusted_partners_for_work_family,
    list_profiles,
    record_signal,
)

router = APIRouter()


@router.get(
    "/partner-trust/profiles",
    response_model=list[PartnerTrustProfileRead],
)
async def list_profiles_endpoint(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_profiles(db)


@router.get(
    "/partner-trust/profiles/{org_id}",
    response_model=PartnerTrustProfileRead,
)
async def get_profile_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_profile(db, org_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Partner trust profile not found")
    return profile


@router.post(
    "/partner-trust/signals",
    response_model=PartnerTrustSignalRead,
    status_code=201,
)
async def record_signal_endpoint(
    payload: TrustSignalCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    signal = await record_signal(db, data)
    # Auto-evaluate after recording signal
    await evaluate_partner(db, payload.partner_org_id)
    await db.commit()
    return signal


@router.get(
    "/partner-trust/profiles/{org_id}/routing-hint",
    response_model=RoutingHintRead,
)
async def get_routing_hint_endpoint(
    org_id: UUID,
    workflow_type: str = "default",
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await get_routing_hint(db, org_id, workflow_type)


# ---------------------------------------------------------------------------
# V3 doctrine endpoints: case-rooted trust
# ---------------------------------------------------------------------------


@router.get(
    "/cases/{case_id}/partner-trust",
    response_model=list[CasePartnerTrustRead],
)
async def get_case_partner_trust_endpoint(
    case_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get trust profiles for all partners involved in a case."""
    return await get_partner_trust_for_case(db, case_id)


@router.get(
    "/partners/{org_id}/trust-profile",
    response_model=PartnerTrustProfileRead,
)
async def get_partner_trust_profile_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get trust profile for a specific partner organization."""
    profile = await get_profile(db, org_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Partner trust profile not found")
    return profile


@router.get(
    "/partners/{org_id}/trusted-for-work-family",
    response_model=list[TrustedPartnerRead],
)
async def get_trusted_partners_endpoint(
    org_id: UUID,
    work_family: str = "general",
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get partners with adequate+ trust for panel selection guidance."""
    return await get_trusted_partners_for_work_family(db, org_id, work_family)
