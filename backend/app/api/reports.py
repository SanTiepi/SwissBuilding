"""API routes for authority report PDF generation (Programme M)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.authority_report_generator import generate_authority_report

router = APIRouter()


@router.post(
    "/buildings/{building_id}/generate-report",
    status_code=201,
)
async def generate_report_endpoint(
    building_id: uuid.UUID,
    type: str = Query("authority", description="Report type"),
    include_photos: bool = Query(True, description="Include photos in report"),
    include_plans: bool = Query(True, description="Include technical plans"),
    language: str = Query("fr", description="Report language"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a 20+ page authority report as HTML payload for PDF conversion.

    The HTML payload can be sent to Gotenberg for professional PDF rendering.
    Returns the HTML, metadata, and a SHA-256 hash for verification.
    """
    if type != "authority":
        raise HTTPException(status_code=400, detail=f"Unsupported report type: {type}")

    result = await generate_authority_report(
        db,
        building_id,
        include_photos=include_photos,
        include_plans=include_plans,
        language=language,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")

    return result
