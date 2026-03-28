"""Transaction Readiness Workflow API routes.

Assess, generate pack, and get buyer summary for building transactions.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.transaction_workflow_service import TransactionWorkflowService

router = APIRouter()

_service = TransactionWorkflowService()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class GeneratePackRequest(BaseModel):
    org_id: UUID | None = None
    redact_financials: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_building_or_404(db: AsyncSession, building_id: UUID, user: User | None = None):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    if user and getattr(user, "role", None) != "admin":
        user_org = getattr(user, "organization_id", None)
        if user_org and building.organization_id != user_org:
            raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/buildings/{building_id}/transaction-workflow/assessment")
async def assess_transaction_readiness(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Full transaction readiness assessment for a building."""
    await _get_building_or_404(db, building_id, current_user)
    try:
        return await _service.assess_transaction_readiness(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/buildings/{building_id}/transaction-workflow/pack")
async def generate_transaction_pack(
    building_id: UUID,
    body: GeneratePackRequest | None = None,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a transaction/due-diligence pack for a building."""
    await _get_building_or_404(db, building_id, current_user)
    redact = body.redact_financials if body else True
    org_id = body.org_id if body else None
    try:
        return await _service.generate_transaction_pack(
            db,
            building_id,
            created_by_id=current_user.id,
            org_id=org_id,
            redact_financials=redact,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/buildings/{building_id}/transaction-workflow/buyer-summary")
async def get_buyer_summary(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Buyer/advisor-facing summary for a building."""
    await _get_building_or_404(db, building_id, current_user)
    try:
        return await _service.get_buyer_summary(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
