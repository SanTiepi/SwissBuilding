"""Building Passport Envelope API — sovereign, versioned, transferable passports."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.passport_envelope import (
    PassportAcknowledgeRequest,
    PassportEnvelopeCreate,
    PassportEnvelopeHistoryResponse,
    PassportEnvelopeResponse,
    PassportReimportRequest,
    PassportSupersedeRequest,
    PassportTransferReceiptResponse,
    PassportTransferRequest,
)
from app.services import passport_envelope_service as svc

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/passport-envelope",
    response_model=PassportEnvelopeResponse,
    status_code=201,
)
async def create_envelope_endpoint(
    building_id: UUID,
    data: PassportEnvelopeCreate,
    current_user: User = Depends(require_permission("evidence_packs", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new passport envelope from current building state."""
    await _get_building_or_404(db, building_id)
    try:
        envelope = await svc.create_envelope(
            db,
            building_id=building_id,
            org_id=current_user.organization_id,
            created_by_id=current_user.id,
            redaction_profile=data.redaction_profile,
            version_label=data.version_label,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(envelope)
    return envelope


@router.get(
    "/buildings/{building_id}/passport-envelope",
    response_model=PassportEnvelopeResponse,
)
async def get_latest_envelope_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest sovereign passport envelope for a building."""
    await _get_building_or_404(db, building_id)
    envelope = await svc.get_latest_envelope(db, building_id)
    if not envelope:
        raise HTTPException(status_code=404, detail="No passport envelope found")
    return envelope


@router.get(
    "/buildings/{building_id}/passport-envelope/history",
    response_model=PassportEnvelopeHistoryResponse,
)
async def get_envelope_history_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get version history of all passport envelopes for a building."""
    await _get_building_or_404(db, building_id)
    items = await svc.get_envelope_history(db, building_id)
    return {"items": items, "count": len(items)}


@router.post(
    "/passport-envelope/{envelope_id}/freeze",
    response_model=PassportEnvelopeResponse,
)
async def freeze_envelope_endpoint(
    envelope_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Freeze a passport envelope. No further edits possible."""
    try:
        envelope = await svc.freeze_envelope(db, envelope_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(envelope)
    return envelope


@router.post(
    "/passport-envelope/{envelope_id}/publish",
    response_model=PassportEnvelopeResponse,
)
async def publish_envelope_endpoint(
    envelope_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Publish a passport envelope. Must be frozen first."""
    try:
        envelope = await svc.publish_envelope(db, envelope_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(envelope)
    return envelope


@router.post(
    "/passport-envelope/{envelope_id}/transfer",
    response_model=PassportTransferReceiptResponse,
)
async def transfer_envelope_endpoint(
    envelope_id: UUID,
    data: PassportTransferRequest,
    current_user: User = Depends(require_permission("evidence_packs", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Transfer a passport envelope to a recipient. Creates a transfer receipt."""
    try:
        receipt = await svc.transfer_envelope(
            db,
            envelope_id=envelope_id,
            transferred_by_id=current_user.id,
            sender_org_id=current_user.organization_id,
            recipient_type=data.recipient_type,
            recipient_id=data.recipient_id,
            recipient_name=data.recipient_name,
            delivery_method=data.delivery_method,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(receipt)
    return receipt


@router.post(
    "/passport-envelope/receipts/{receipt_id}/acknowledge",
    response_model=PassportTransferReceiptResponse,
)
async def acknowledge_receipt_endpoint(
    receipt_id: UUID,
    data: PassportAcknowledgeRequest,
    current_user: User = Depends(require_permission("evidence_packs", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Recipient acknowledges receipt of a passport envelope."""
    try:
        receipt = await svc.acknowledge_receipt(
            db,
            receipt_id=receipt_id,
            acknowledged_by_name=data.acknowledged_by_name,
            receipt_hash=data.receipt_hash,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(receipt)
    return receipt


@router.post(
    "/passport-envelope/{envelope_id}/supersede",
    response_model=PassportEnvelopeResponse,
)
async def supersede_envelope_endpoint(
    envelope_id: UUID,
    data: PassportSupersedeRequest,
    current_user: User = Depends(require_permission("evidence_packs", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Mark an envelope as superseded by a newer one.

    The envelope_id in the path is the NEW envelope.
    The old envelope to supersede must be the current sovereign.
    """
    # Find the current sovereign for the same building
    new_envelope = await svc.get_envelope(db, envelope_id)
    if not new_envelope:
        raise HTTPException(status_code=404, detail="Envelope not found")

    current_sovereign = await svc.get_latest_envelope(db, new_envelope.building_id)
    if not current_sovereign or current_sovereign.id == envelope_id:
        raise HTTPException(status_code=400, detail="No previous sovereign envelope to supersede")

    try:
        await svc.supersede_envelope(
            db,
            old_envelope_id=current_sovereign.id,
            new_envelope_id=envelope_id,
            reason=data.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(new_envelope)
    return new_envelope


@router.post(
    "/buildings/{building_id}/passport-envelope/reimport",
    response_model=PassportEnvelopeResponse,
    status_code=201,
)
async def reimport_envelope_endpoint(
    building_id: UUID,
    data: PassportReimportRequest,
    current_user: User = Depends(require_permission("evidence_packs", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Re-import a previously exported passport envelope into a building."""
    await _get_building_or_404(db, building_id)
    try:
        envelope = await svc.reimport_envelope(
            db,
            envelope_data=data.envelope_data,
            building_id=building_id,
            imported_by_id=current_user.id,
            org_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(envelope)
    return envelope
