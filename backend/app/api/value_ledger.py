"""BatiConnect — Value Ledger API routes.

Endpoints for the cumulative value accumulation system.
Shows organizations how much value BatiConnect has delivered over time.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.value_ledger import ValueEvent, ValueLedger
from app.services.value_ledger_service import get_value_events, get_value_ledger

router = APIRouter()


@router.get("/organizations/{org_id}/value-ledger", response_model=ValueLedger)
async def get_org_value_ledger(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Current cumulative value ledger for an organization."""
    ledger = await get_value_ledger(db, org_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Organization not found or has no buildings")
    return ledger


@router.get("/organizations/{org_id}/value-events", response_model=list[ValueEvent])
async def get_org_value_events(
    org_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Recent value events for an organization."""
    return await get_value_events(db, org_id, limit=limit)
