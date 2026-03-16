"""Building dossier generation API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.dossier_service import generate_building_dossier, generate_dossier_preview

router = APIRouter()


@router.post("/buildings/{building_id}/dossier")
async def create_dossier(
    building_id: uuid.UUID,
    stage: str = Query(default="avt", pattern="^(avt|apt)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete building dossier.

    Returns PDF if Gotenberg is available, otherwise returns HTML with metadata.
    """
    try:
        result = await generate_building_dossier(db, building_id, current_user.id, stage=stage)
    except ValueError:
        raise HTTPException(status_code=404, detail="Building not found") from None

    if result["pdf_bytes"]:
        return Response(
            content=result["pdf_bytes"],
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=dossier-{building_id}.pdf"},
        )

    return {
        "export_job_id": result["export_job_id"],
        "format": "html",
        "html": result["html"],
    }


@router.get("/buildings/{building_id}/dossier/preview")
async def preview_dossier(
    building_id: uuid.UUID,
    stage: str = Query(default="avt", pattern="^(avt|apt)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return an HTML preview of the building dossier."""
    try:
        html = await generate_dossier_preview(db, building_id, stage=stage)
    except ValueError:
        raise HTTPException(status_code=404, detail="Building not found") from None

    return HTMLResponse(content=html)
