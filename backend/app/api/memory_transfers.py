"""Memory transfer API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.memory_transfer import (
    MemoryCompilation,
    MemoryContinuityScore,
    MemoryTransferAccept,
    MemoryTransferContest,
    MemoryTransferCreate,
    MemoryTransferList,
    MemoryTransferRead,
    TransferReadiness,
)
from app.services import memory_transfer_service as svc

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/memory-transfers",
    response_model=MemoryTransferRead,
    status_code=201,
)
async def initiate_transfer_endpoint(
    building_id: UUID,
    data: MemoryTransferCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a memory transfer for a building."""
    await _get_building_or_404(db, building_id)
    try:
        transfer = await svc.initiate_transfer(
            db,
            building_id=building_id,
            transfer_type=data.transfer_type,
            from_org_id=data.from_org_id,
            to_org_id=data.to_org_id,
            user_id=current_user.id,
            transfer_label=data.transfer_label,
            from_user_id=data.from_user_id,
            to_user_id=data.to_user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.get(
    "/buildings/{building_id}/memory-transfers",
    response_model=MemoryTransferList,
)
async def list_transfers_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all memory transfers for a building — the continuity chain."""
    await _get_building_or_404(db, building_id)
    transfers = await svc.get_transfer_history(db, building_id)
    return MemoryTransferList(items=transfers, count=len(transfers))


@router.get(
    "/buildings/{building_id}/transfer-readiness",
    response_model=TransferReadiness,
)
async def check_readiness_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Check if a building's memory can be cleanly transferred."""
    readiness = await svc.check_transfer_readiness(db, building_id)
    return readiness


@router.get(
    "/memory-transfers/{transfer_id}",
    response_model=MemoryTransferRead,
)
async def get_transfer_endpoint(
    transfer_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific memory transfer."""
    from sqlalchemy import select

    from app.models.memory_transfer import MemoryTransfer

    result = await db.execute(select(MemoryTransfer).where(MemoryTransfer.id == transfer_id))
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfert introuvable")
    return transfer


@router.post(
    "/memory-transfers/{transfer_id}/compile",
    response_model=MemoryCompilation,
)
async def compile_memory_endpoint(
    transfer_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Compile the complete building memory for a transfer."""
    try:
        compilation = await svc.compile_memory(db, transfer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    return compilation


@router.post(
    "/memory-transfers/{transfer_id}/submit-review",
    response_model=MemoryTransferRead,
)
async def submit_review_endpoint(
    transfer_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Submit compiled memory for recipient review."""
    try:
        transfer = await svc.submit_for_review(db, transfer_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.post(
    "/memory-transfers/{transfer_id}/accept",
    response_model=MemoryTransferRead,
)
async def accept_transfer_endpoint(
    transfer_id: UUID,
    data: MemoryTransferAccept,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Recipient accepts the transferred memory."""
    try:
        transfer = await svc.accept_transfer(db, transfer_id, current_user.id, data.comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.post(
    "/memory-transfers/{transfer_id}/contest",
    response_model=MemoryTransferRead,
)
async def contest_transfer_endpoint(
    transfer_id: UUID,
    data: MemoryTransferContest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Recipient contests the transferred memory."""
    try:
        transfer = await svc.contest_transfer(db, transfer_id, current_user.id, data.comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.post(
    "/memory-transfers/{transfer_id}/complete",
    response_model=MemoryTransferRead,
)
async def complete_transfer_endpoint(
    transfer_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Finalize transfer after acceptance."""
    try:
        transfer = await svc.complete_transfer(db, transfer_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.get(
    "/buildings/{building_id}/continuity-score",
    response_model=MemoryContinuityScore,
)
async def continuity_score_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get memory continuity score for a building."""
    await _get_building_or_404(db, building_id)
    score = await svc.compute_continuity_score(db, building_id)
    return score
