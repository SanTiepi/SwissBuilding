"""
SwissBuildingOS - Risk Communication API

4 GET endpoints for risk communication generation and audit.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.risk_communication import (
    CommunicationLog,
    OccupantNotice,
    StakeholderNotification,
    WorkerSafetyBriefing,
)
from app.services.risk_communication_service import (
    generate_occupant_notice,
    generate_stakeholder_notification,
    generate_worker_safety_briefing,
    get_communication_log,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/risk-communication/occupant-notice",
    response_model=OccupantNotice,
)
async def get_occupant_notice(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a plain-language risk notice for building occupants."""
    try:
        return await generate_occupant_notice(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/risk-communication/worker-briefing",
    response_model=WorkerSafetyBriefing,
)
async def get_worker_briefing(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a CFST 6503-aligned worker safety briefing."""
    try:
        return await generate_worker_safety_briefing(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/risk-communication/stakeholder-notification",
    response_model=StakeholderNotification,
)
async def get_stakeholder_notification(
    building_id: UUID,
    audience: str = Query(..., description="Target audience: owner, tenant, authority, insurer"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an audience-specific stakeholder notification."""
    try:
        return await generate_stakeholder_notification(db, building_id, audience)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/risk-communication/log",
    response_model=CommunicationLog,
)
async def get_communication_log_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the communication audit log for a building."""
    try:
        return await get_communication_log(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
