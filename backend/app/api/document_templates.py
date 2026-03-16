"""Document template generation API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.document_template import (
    GeneratedTemplate,
    GenerateTemplateRequest,
    TemplateInfo,
)
from app.services.document_template_service import (
    generate_template,
    get_available_templates,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/templates",
    response_model=list[TemplateInfo],
)
async def list_templates(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List available document templates for a building."""
    templates = await get_available_templates(db, building_id)
    if not templates:
        raise HTTPException(status_code=404, detail="Building not found")
    return templates


@router.post(
    "/buildings/{building_id}/templates/generate",
    response_model=GeneratedTemplate,
)
async def generate_document_template(
    building_id: uuid.UUID,
    request: GenerateTemplateRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a pre-filled document template for a building."""
    try:
        result = await generate_template(db, building_id, request.template_type)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=400, detail=msg) from None
    return result
