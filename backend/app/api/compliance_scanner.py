"""Compliance Scanner API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.compliance_scanner_service import (
    compute_regulatory_deadlines,
    detect_regulatory_anomalies,
    scan_building_compliance,
)

router = APIRouter()


@router.get("/compliance/scan/{building_id}")
async def scan_compliance_endpoint(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Full compliance scan for a building."""
    try:
        result = await scan_building_compliance(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return result


@router.get("/compliance/deadlines/{building_id}")
async def regulatory_deadlines_endpoint(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Calculate regulatory deadlines for a building."""
    try:
        return await compute_regulatory_deadlines(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get("/compliance/anomalies/{building_id}")
async def regulatory_anomalies_endpoint(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect regulatory anomalies for a building."""
    try:
        return await detect_regulatory_anomalies(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
