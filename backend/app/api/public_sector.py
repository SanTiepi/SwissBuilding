"""BatiConnect — Public Sector API routes (municipality / committee / governance)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.public_sector import (
    CirculateRequest,
    CommitteePackCreate,
    CommitteePackRead,
    DecisionTraceCreate,
    DecisionTraceRead,
    GovernanceSignalRead,
    PublicOwnerModeCreate,
    PublicOwnerModeRead,
    ReviewPackCreate,
    ReviewPackRead,
)
from app.services.public_sector_service import (
    activate_public_mode,
    circulate_review_pack,
    generate_committee_pack,
    generate_review_pack,
    get_committee_packs,
    get_decision_traces,
    get_governance_signals,
    get_public_mode,
    get_review_packs,
    record_decision,
    resolve_signal,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---- Operating Mode ----


@router.post(
    "/organizations/{org_id}/public-owner-mode",
    response_model=PublicOwnerModeRead,
    status_code=201,
)
async def activate_public_mode_endpoint(
    org_id: UUID,
    payload: PublicOwnerModeCreate,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    mode = await activate_public_mode(db, org_id, data)
    await db.commit()
    return mode


@router.get(
    "/organizations/{org_id}/public-owner-mode",
    response_model=PublicOwnerModeRead,
)
async def get_public_mode_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    mode = await get_public_mode(db, org_id)
    if not mode:
        raise HTTPException(status_code=404, detail="Public owner mode not configured")
    return mode


# ---- Review Packs ----


@router.post(
    "/buildings/{building_id}/review-packs",
    response_model=ReviewPackRead,
    status_code=201,
)
async def generate_review_pack_endpoint(
    building_id: UUID,
    payload: ReviewPackCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    pack = await generate_review_pack(
        db, building_id, current_user.id, notes=payload.notes, review_deadline=payload.review_deadline
    )
    await db.commit()
    return pack


@router.get(
    "/buildings/{building_id}/review-packs",
    response_model=list[ReviewPackRead],
)
async def list_review_packs_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_review_packs(db, building_id)


@router.post(
    "/review-packs/{pack_id}/circulate",
    response_model=ReviewPackRead,
)
async def circulate_review_pack_endpoint(
    pack_id: UUID,
    payload: CirculateRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        pack = await circulate_review_pack(db, pack_id, payload.recipients)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    await db.commit()
    return pack


# ---- Committee Packs ----


@router.post(
    "/buildings/{building_id}/committee-packs",
    response_model=CommitteePackRead,
    status_code=201,
)
async def generate_committee_pack_endpoint(
    building_id: UUID,
    payload: CommitteePackCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    pack = await generate_committee_pack(db, building_id, data)
    await db.commit()
    return pack


@router.get(
    "/buildings/{building_id}/committee-packs",
    response_model=list[CommitteePackRead],
)
async def list_committee_packs_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_committee_packs(db, building_id)


# ---- Decision Traces ----


@router.post(
    "/committee-packs/{pack_id}/decide",
    response_model=DecisionTraceRead,
    status_code=201,
)
async def record_committee_decision_endpoint(
    pack_id: UUID,
    payload: DecisionTraceCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    data["pack_type"] = "committee"
    data["pack_id"] = pack_id
    trace = await record_decision(db, data)
    await db.commit()
    return trace


@router.get(
    "/decision-traces/{pack_type}/{pack_id}",
    response_model=list[DecisionTraceRead],
)
async def list_decision_traces_endpoint(
    pack_type: str,
    pack_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await get_decision_traces(db, pack_type, pack_id)


# ---- Governance Signals ----


@router.get(
    "/organizations/{org_id}/governance-signals",
    response_model=list[GovernanceSignalRead],
)
async def list_governance_signals_endpoint(
    org_id: UUID,
    building_id: UUID | None = None,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await get_governance_signals(db, org_id, building_id)


@router.post(
    "/governance-signals/{signal_id}/resolve",
    response_model=GovernanceSignalRead,
)
async def resolve_governance_signal_endpoint(
    signal_id: UUID,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    try:
        signal = await resolve_signal(db, signal_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    await db.commit()
    return signal
