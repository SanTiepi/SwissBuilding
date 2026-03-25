"""BatiConnect — Proof Delivery API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.proof_delivery import ProofDeliveryCreate, ProofDeliveryRead, ProofDeliveryTransition
from app.services.proof_delivery_service import (
    create_delivery,
    get_deliveries_for_building,
    get_delivery,
    mark_acknowledged,
    mark_delivered,
    mark_failed,
    mark_sent,
    mark_viewed,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


async def _get_delivery_or_404(db: AsyncSession, delivery_id: UUID):
    delivery = await get_delivery(db, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Proof delivery not found")
    return delivery


@router.post(
    "/buildings/{building_id}/proof-deliveries",
    response_model=ProofDeliveryRead,
    status_code=201,
)
async def create_proof_delivery_endpoint(
    building_id: UUID,
    payload: ProofDeliveryCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    data = payload.model_dump(exclude_unset=True)
    data.pop("building_id", None)
    delivery = await create_delivery(db, building_id, data, created_by=current_user.id)
    await db.commit()
    return delivery


@router.get(
    "/buildings/{building_id}/proof-deliveries",
    response_model=list[ProofDeliveryRead],
)
async def list_proof_deliveries_endpoint(
    building_id: UUID,
    audience: str | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_building_or_404(db, building_id)
    return await get_deliveries_for_building(db, building_id, audience=audience, status=status)


@router.get(
    "/proof-deliveries/{delivery_id}",
    response_model=ProofDeliveryRead,
)
async def get_proof_delivery_endpoint(
    delivery_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await _get_delivery_or_404(db, delivery_id)


@router.post(
    "/proof-deliveries/{delivery_id}/sent",
    response_model=ProofDeliveryRead,
)
async def mark_sent_endpoint(
    delivery_id: UUID,
    payload: ProofDeliveryTransition | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_delivery_or_404(db, delivery_id)
    kwargs = payload.model_dump(exclude_unset=True) if payload else {}
    delivery = await mark_sent(db, delivery_id, **kwargs)
    await db.commit()
    return delivery


@router.post(
    "/proof-deliveries/{delivery_id}/delivered",
    response_model=ProofDeliveryRead,
)
async def mark_delivered_endpoint(
    delivery_id: UUID,
    payload: ProofDeliveryTransition | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_delivery_or_404(db, delivery_id)
    kwargs = payload.model_dump(exclude_unset=True) if payload else {}
    delivery = await mark_delivered(db, delivery_id, **kwargs)
    await db.commit()
    return delivery


@router.post(
    "/proof-deliveries/{delivery_id}/viewed",
    response_model=ProofDeliveryRead,
)
async def mark_viewed_endpoint(
    delivery_id: UUID,
    payload: ProofDeliveryTransition | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_delivery_or_404(db, delivery_id)
    kwargs = payload.model_dump(exclude_unset=True) if payload else {}
    delivery = await mark_viewed(db, delivery_id, **kwargs)
    await db.commit()
    return delivery


@router.post(
    "/proof-deliveries/{delivery_id}/acknowledged",
    response_model=ProofDeliveryRead,
)
async def mark_acknowledged_endpoint(
    delivery_id: UUID,
    payload: ProofDeliveryTransition | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_delivery_or_404(db, delivery_id)
    kwargs = payload.model_dump(exclude_unset=True) if payload else {}
    delivery = await mark_acknowledged(db, delivery_id, **kwargs)
    await db.commit()
    return delivery


@router.post(
    "/proof-deliveries/{delivery_id}/failed",
    response_model=ProofDeliveryRead,
)
async def mark_failed_endpoint(
    delivery_id: UUID,
    payload: ProofDeliveryTransition,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    await _get_delivery_or_404(db, delivery_id)
    if not payload.error_message:
        raise HTTPException(status_code=400, detail="error_message is required for failed transition")
    delivery = await mark_failed(db, delivery_id, error_message=payload.error_message, notes=payload.notes)
    await db.commit()
    return delivery
