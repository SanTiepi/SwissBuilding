"""Truth Rituals API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.truth_ritual import (
    TruthRitualAcknowledge,
    TruthRitualFreeze,
    TruthRitualList,
    TruthRitualPublish,
    TruthRitualReceipt,
    TruthRitualReopen,
    TruthRitualResponse,
    TruthRitualSupersede,
    TruthRitualTransfer,
    TruthRitualValidate,
)
from app.services import ritual_service as svc

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/rituals/validate",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def validate_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualValidate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Validate an artifact. Records who validated, when, and why."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.validate(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            validated_by_id=current_user.id,
            org_id=current_user.organization_id,
            reason=data.reason,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.post(
    "/buildings/{building_id}/rituals/freeze",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def freeze_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualFreeze,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Freeze an artifact. Computes content hash. No further edits allowed."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.freeze(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            frozen_by_id=current_user.id,
            org_id=current_user.organization_id,
            reason=data.reason,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.post(
    "/buildings/{building_id}/rituals/publish",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def publish_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualPublish,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Publish an artifact. Computes hash, increments version."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.publish(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            published_by_id=current_user.id,
            org_id=current_user.organization_id,
            recipient_type=data.recipient_type,
            recipient_id=data.recipient_id,
            delivery_method=data.delivery_method,
            reason=data.reason,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.post(
    "/buildings/{building_id}/rituals/transfer",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def transfer_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualTransfer,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Transfer a sovereign artifact to a recipient."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.transfer(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            transferred_by_id=current_user.id,
            org_id=current_user.organization_id,
            recipient_type=data.recipient_type,
            recipient_id=data.recipient_id,
            delivery_method=data.delivery_method,
            reason=data.reason,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.post(
    "/buildings/{building_id}/rituals/acknowledge",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def acknowledge_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualAcknowledge,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge receipt of an artifact."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.acknowledge(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            acknowledged_by_id=current_user.id,
            org_id=current_user.organization_id,
            receipt_hash=data.receipt_hash,
            reason=data.reason,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.post(
    "/buildings/{building_id}/rituals/reopen",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def reopen_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualReopen,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Reopen a previously frozen or published artifact. Reason is required."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.reopen(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            reopened_by_id=current_user.id,
            org_id=current_user.organization_id,
            reason=data.reason,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.post(
    "/buildings/{building_id}/rituals/supersede",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def supersede_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualSupersede,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Mark an artifact as superseded by a newer version."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.supersede(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            superseded_by_id=current_user.id,
            org_id=current_user.organization_id,
            new_target_id=data.new_target_id,
            reason=data.reason,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.post(
    "/buildings/{building_id}/rituals/receipt",
    response_model=TruthRitualResponse,
    status_code=201,
)
async def receipt_ritual_endpoint(
    building_id: UUID,
    data: TruthRitualReceipt,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record cryptographic or timestamped proof of delivery."""
    await _get_building_or_404(db, building_id)
    try:
        ritual = await svc.receipt(
            db,
            building_id=building_id,
            target_type=data.target_type,
            target_id=data.target_id,
            recipient_id=data.recipient_id,
            org_id=current_user.organization_id,
            receipt_hash=data.receipt_hash,
            delivery_method=data.delivery_method,
            performed_by_id=current_user.id,
            case_id=data.case_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ritual)
    return ritual


@router.get(
    "/buildings/{building_id}/rituals",
    response_model=TruthRitualList,
)
async def list_rituals_endpoint(
    building_id: UUID,
    target_type: str | None = Query(None),
    target_id: UUID | None = Query(None),
    ritual_type: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get ritual history for a building with optional filters."""
    await _get_building_or_404(db, building_id)
    items = await svc.get_ritual_history(
        db,
        building_id=building_id,
        target_type=target_type,
        target_id=target_id,
        ritual_type=ritual_type,
    )
    return {"items": items, "count": len(items)}
