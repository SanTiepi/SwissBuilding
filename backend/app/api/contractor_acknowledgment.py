"""Contractor acknowledgment workflow API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.contractor_acknowledgment import (
    ContractorAcknowledgmentAck,
    ContractorAcknowledgmentCreate,
    ContractorAcknowledgmentList,
    ContractorAcknowledgmentRefuse,
    ContractorAcknowledgmentResponse,
)
from app.services import contractor_acknowledgment_service as svc

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.post(
    "/buildings/{building_id}/contractor-acknowledgments",
    response_model=ContractorAcknowledgmentResponse,
    status_code=201,
)
async def create_acknowledgment_endpoint(
    building_id: UUID,
    data: ContractorAcknowledgmentCreate,
    current_user: User = Depends(require_permission("interventions", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new contractor acknowledgment for a building intervention."""
    await _get_building_or_404(db, building_id)
    try:
        ack = await svc.create_acknowledgment(db, building_id, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ack)
    return ack


@router.get(
    "/buildings/{building_id}/contractor-acknowledgments",
    response_model=ContractorAcknowledgmentList,
)
async def list_building_acknowledgments_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("interventions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all contractor acknowledgments for a building."""
    await _get_building_or_404(db, building_id)
    items = await svc.list_for_building(db, building_id)
    return {"items": items, "count": len(items)}


@router.get(
    "/contractor-acknowledgments/mine",
    response_model=ContractorAcknowledgmentList,
)
async def list_my_acknowledgments_endpoint(
    current_user: User = Depends(require_permission("interventions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all contractor acknowledgments assigned to the current user."""
    items = await svc.list_for_contractor(db, current_user.id)
    return {"items": items, "count": len(items)}


@router.get(
    "/contractor-acknowledgments/{ack_id}",
    response_model=ContractorAcknowledgmentResponse,
)
async def get_acknowledgment_endpoint(
    ack_id: UUID,
    current_user: User = Depends(require_permission("interventions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single contractor acknowledgment."""
    ack = await svc.get_acknowledgment(db, ack_id)
    if not ack:
        raise HTTPException(status_code=404, detail="Contractor acknowledgment not found")
    return ack


@router.post(
    "/contractor-acknowledgments/{ack_id}/send",
    response_model=ContractorAcknowledgmentResponse,
)
async def send_acknowledgment_endpoint(
    ack_id: UUID,
    current_user: User = Depends(require_permission("interventions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Send an acknowledgment to the contractor."""
    try:
        ack = await svc.send_acknowledgment(db, ack_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ack)
    return ack


@router.post(
    "/contractor-acknowledgments/{ack_id}/view",
    response_model=ContractorAcknowledgmentResponse,
)
async def view_acknowledgment_endpoint(
    ack_id: UUID,
    current_user: User = Depends(require_permission("interventions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Mark an acknowledgment as viewed by the contractor."""
    try:
        ack = await svc.view_acknowledgment(db, ack_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ack)
    return ack


@router.post(
    "/contractor-acknowledgments/{ack_id}/acknowledge",
    response_model=ContractorAcknowledgmentResponse,
)
async def acknowledge_endpoint(
    ack_id: UUID,
    data: ContractorAcknowledgmentAck,
    request: Request,
    current_user: User = Depends(require_permission("interventions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Contractor acknowledges receipt and understanding of safety requirements."""
    ip_address = request.client.host if request.client else None
    try:
        ack = await svc.acknowledge(db, ack_id, notes=data.contractor_notes, ip_address=ip_address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ack)
    return ack


@router.post(
    "/contractor-acknowledgments/{ack_id}/refuse",
    response_model=ContractorAcknowledgmentResponse,
)
async def refuse_acknowledgment_endpoint(
    ack_id: UUID,
    data: ContractorAcknowledgmentRefuse,
    current_user: User = Depends(require_permission("interventions", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Contractor refuses the acknowledgment with a reason."""
    try:
        ack = await svc.refuse(db, ack_id, reason=data.refusal_reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    await db.commit()
    await db.refresh(ack)
    return ack
