"""Proof of State API routes.

Exportable building state snapshots for insurance, bank, tribunal, or sale.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.proof_of_state import ProofOfStateRead, ProofOfStateSummaryRead
from app.services.proof_of_state_service import (
    generate_proof_of_state,
    generate_proof_of_state_summary,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/proof-of-state",
    response_model=ProofOfStateRead,
)
async def get_proof_of_state(
    building_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return a full proof-of-state export for a building."""
    result = await generate_proof_of_state(db, building_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return JSONResponse(
        content=result,
        headers={
            "Content-Disposition": f'attachment; filename="proof-of-state-{building_id}.json"',
        },
    )


@router.get(
    "/buildings/{building_id}/proof-of-state/summary",
    response_model=ProofOfStateSummaryRead,
)
async def get_proof_of_state_summary(
    building_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return a compact proof-of-state summary."""
    result = await generate_proof_of_state_summary(db, building_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return JSONResponse(
        content=result,
        headers={
            "Content-Disposition": f'attachment; filename="proof-of-state-summary-{building_id}.json"',
        },
    )
