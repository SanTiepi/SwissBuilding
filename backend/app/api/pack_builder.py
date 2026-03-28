"""Pack Builder API routes — multi-audience pack generation."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.pack_builder import (
    AvailablePacksResponse,
    PackGenerateRequest,
    PackResult,
)
from app.services.pack_builder_service import (
    generate_pack,
    list_available_packs,
)

router = APIRouter()


@router.post(
    "/buildings/{building_id}/packs/{pack_type}",
    response_model=PackResult,
    status_code=201,
)
async def generate_pack_endpoint(
    building_id: UUID,
    pack_type: str,
    body: PackGenerateRequest | None = None,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an audience-specific pack for a building."""
    try:
        result = await generate_pack(
            db,
            building_id,
            pack_type,
            org_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
            created_by_id=current_user.id,
            redact_financials=body.redact_financials if body else False,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.get(
    "/buildings/{building_id}/packs",
    response_model=AvailablePacksResponse,
)
async def list_available_packs_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List available pack types with readiness indicators for a building."""
    try:
        result = await list_available_packs(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result
