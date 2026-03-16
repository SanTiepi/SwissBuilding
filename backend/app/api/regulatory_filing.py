"""Regulatory filing API routes (SUVA, cantonal declarations, OLED waste manifests)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.regulatory_filing import (
    CantonalDeclaration,
    FilingStatus,
    SuvaNotification,
    WasteManifest,
)
from app.services.regulatory_filing_service import (
    generate_cantonal_declaration,
    generate_suva_notification,
    generate_waste_manifest,
    get_filing_status,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/regulatory-filings/suva",
    response_model=SuvaNotification,
)
async def get_suva_notification(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate SUVA asbestos notification data (CFST 6503)."""
    try:
        return await generate_suva_notification(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/regulatory-filings/cantonal-declaration",
    response_model=CantonalDeclaration,
)
async def get_cantonal_declaration(
    building_id: UUID,
    canton: str | None = Query(None, description="Canton code (e.g. VD, GE). Defaults to building's canton."),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate canton-specific pollutant declaration."""
    try:
        return await generate_cantonal_declaration(db, building_id, canton=canton)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/regulatory-filings/waste-manifest",
    response_model=WasteManifest,
)
async def get_waste_manifest(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate OLED waste tracking manifest."""
    try:
        return await generate_waste_manifest(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/regulatory-filings/status",
    response_model=FilingStatus,
)
async def get_building_filing_status(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get regulatory filing status for a building."""
    try:
        return await get_filing_status(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
