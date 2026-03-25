"""BatiConnect — Partner trust API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.partner_trust import (
    PartnerTrustProfileRead,
    PartnerTrustSignalRead,
    RoutingHintRead,
    TrustSignalCreate,
)
from app.services.partner_trust_service import (
    evaluate_partner,
    get_profile,
    get_routing_hint,
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
