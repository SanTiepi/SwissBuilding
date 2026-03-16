"""Handoff pack generation API routes.

Provides endpoints for generating structured handoff packs at three
transition points (diagnostic, contractor, authority) and validating
completeness before handoff.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.handoff_pack import (
    AuthorityHandoffResult,
    ContractorHandoffResult,
    DiagnosticHandoffResult,
    HandoffValidationResult,
)
from app.services.handoff_pack_service import (
    generate_authority_handoff,
    generate_contractor_handoff,
    generate_diagnostic_handoff,
    validate_handoff_completeness,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/handoff/diagnostic",
    response_model=DiagnosticHandoffResult,
)
async def get_diagnostic_handoff(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a handoff pack from diagnostician to property manager."""
    try:
        return await generate_diagnostic_handoff(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/handoff/contractor",
    response_model=ContractorHandoffResult,
)
async def get_contractor_handoff(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a handoff pack from property manager to contractor."""
    try:
        return await generate_contractor_handoff(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/handoff/authority",
    response_model=AuthorityHandoffResult,
)
async def get_authority_handoff(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a handoff pack from property manager to authority."""
    try:
        return await generate_authority_handoff(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/handoff/validate",
    response_model=HandoffValidationResult,
)
async def validate_handoff(
    building_id: UUID,
    type: str = Query(..., description="Handoff type: diagnostic, contractor, or authority"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Validate completeness for a given handoff type."""
    try:
        return await validate_handoff_completeness(db, building_id, type)
    except ValueError as e:
        if "Invalid handoff_type" in str(e):
            raise HTTPException(status_code=400, detail=str(e)) from e
        raise HTTPException(status_code=404, detail=str(e)) from e
