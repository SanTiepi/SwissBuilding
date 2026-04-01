"""API routes for building reports and readiness radar."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.building_report_generator import (
    generate_full_report,
    generate_report_pdf_payload,
)
from app.services.readiness_radar_service import compute_readiness_radar

router = APIRouter()


@router.get("/reports/{building_id}/full")
async def building_full_report(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a comprehensive JSON report for a building."""
    result = await generate_full_report(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.post("/reports/{building_id}/pdf")
async def building_pdf_report(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate PDF report HTML payload.

    In production, this payload is sent to Gotenberg for PDF conversion.
    Returns the HTML payload and a status indicator.
    """
    html = await generate_report_pdf_payload(db, building_id)
    if html is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return {
        "building_id": str(building_id),
        "status": "generated",
        "html_payload_length": len(html),
        "html_payload": html,
        "message": "HTML payload ready for Gotenberg PDF conversion",
    }


@router.get("/reports/{building_id}/readiness-radar")
async def building_readiness_radar(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return 7-axis readiness radar data for a building."""
    result = await compute_readiness_radar(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
