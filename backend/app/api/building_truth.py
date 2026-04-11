from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_truth import (
    BuildingClaimCreate,
    BuildingClaimRead,
    BuildingDecisionCreate,
    BuildingDecisionRead,
    ClaimContestRequest,
    DecisionReverseRequest,
    TruthStateRead,
)
from app.schemas.common import PaginatedResponse
from app.services import truth_service

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ── Claims ──


@router.post(
    "/buildings/{building_id}/claims",
    response_model=BuildingClaimRead,
    status_code=201,
    tags=["Building Truth"],
)
async def create_claim_endpoint(
    building_id: UUID,
    data: BuildingClaimCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new building claim (assertion about building state)."""
    await _get_building_or_404(db, building_id)
    claim = await truth_service.create_claim(db, building_id, data, current_user.id, current_user.organization_id)
    await db.commit()
    await db.refresh(claim)
    return claim


@router.get(
    "/buildings/{building_id}/claims",
    response_model=PaginatedResponse[BuildingClaimRead],
    tags=["Building Truth"],
)
async def list_claims_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    claim_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List claims for a building."""
    await _get_building_or_404(db, building_id)
    items, total = await truth_service.list_claims(db, building_id, status, claim_type, page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.post(
    "/claims/{claim_id}/verify",
    response_model=BuildingClaimRead,
    tags=["Building Truth"],
)
async def verify_claim_endpoint(
    claim_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Verify a claim (expert confirmation)."""
    try:
        claim = await truth_service.verify_claim(db, claim_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(claim)
    return claim


@router.post(
    "/claims/{claim_id}/contest",
    response_model=BuildingClaimRead,
    tags=["Building Truth"],
)
async def contest_claim_endpoint(
    claim_id: UUID,
    data: ClaimContestRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Contest a claim. Creates visibility — never silent override."""
    try:
        claim = await truth_service.contest_claim(db, claim_id, current_user.id, data.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(claim)
    return claim


# ── Decisions ──


@router.post(
    "/buildings/{building_id}/decisions",
    response_model=BuildingDecisionRead,
    status_code=201,
    tags=["Building Truth"],
)
async def record_decision_endpoint(
    building_id: UUID,
    data: BuildingDecisionCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a building decision with full provenance."""
    await _get_building_or_404(db, building_id)
    decision = await truth_service.record_decision(db, building_id, data, current_user.id, current_user.organization_id)
    await db.commit()
    await db.refresh(decision)
    return decision


@router.get(
    "/buildings/{building_id}/decisions",
    response_model=PaginatedResponse[BuildingDecisionRead],
    tags=["Building Truth"],
)
async def list_decisions_endpoint(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    decision_type: str | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List decisions for a building."""
    await _get_building_or_404(db, building_id)
    items, total = await truth_service.list_decisions(db, building_id, status, decision_type, page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.post(
    "/decisions/{decision_id}/reverse",
    response_model=BuildingDecisionRead,
    tags=["Building Truth"],
)
async def reverse_decision_endpoint(
    decision_id: UUID,
    data: DecisionReverseRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Reverse a decision. Records who and why."""
    try:
        decision = await truth_service.reverse_decision(db, decision_id, current_user.id, data.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(decision)
    return decision


# ── Truth state ──


@router.get(
    "/buildings/{building_id}/truth-state",
    response_model=TruthStateRead,
    tags=["Building Truth"],
)
async def truth_state_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the current truth state: active claims, contested claims, recent decisions."""
    await _get_building_or_404(db, building_id)
    return await truth_service.get_truth_state(db, building_id)
