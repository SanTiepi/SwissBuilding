"""Dossier Completion Agent API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.dossier_completion import DossierCompletionReport
from app.services.dossier_completion_agent import run_dossier_completion

router = APIRouter()


@router.get(
    "/buildings/{building_id}/dossier-completion",
    response_model=DossierCompletionReport,
)
async def get_dossier_completion(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Run the dossier completion agent and return the report."""
    report = await run_dossier_completion(db, building_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return report


@router.post(
    "/buildings/{building_id}/dossier-completion/refresh",
    response_model=DossierCompletionReport,
)
async def refresh_dossier_completion(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "write")),
    db: AsyncSession = Depends(get_db),
):
    """Force refresh all underlying data and return the dossier completion report."""
    report = await run_dossier_completion(db, building_id, force_refresh=True)
    if report is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return report
