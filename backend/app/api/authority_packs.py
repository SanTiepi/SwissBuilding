"""Authority pack generation API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.authority_pack import (
    AuthorityPackArtifactResult,
    AuthorityPackConfig,
    AuthorityPackListItem,
    AuthorityPackResult,
)
from app.services.authority_pack_service import (
    generate_authority_pack,
    generate_pack_artifact,
    get_authority_pack,
    list_authority_packs,
)

router = APIRouter()


@router.post(
    "/buildings/{building_id}/authority-packs/generate",
    response_model=AuthorityPackResult,
    status_code=201,
)
async def generate_authority_pack_endpoint(
    building_id: UUID,
    config: AuthorityPackConfig,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an authority-ready evidence pack for a building."""
    config.building_id = building_id
    try:
        result = await generate_authority_pack(db, building_id, config, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.post(
    "/buildings/{building_id}/authority-pack/artifact",
    response_model=AuthorityPackArtifactResult,
    status_code=201,
)
async def generate_pack_artifact_endpoint(
    building_id: UUID,
    config: AuthorityPackConfig,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an authority pack and write it as a downloadable JSON artifact file."""
    config.building_id = building_id
    try:
        result = await generate_pack_artifact(db, building_id, config, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.get(
    "/buildings/{building_id}/authority-packs",
    response_model=list[AuthorityPackListItem],
)
async def list_authority_packs_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List previously generated authority packs for a building."""
    return await list_authority_packs(db, building_id)


@router.get(
    "/authority-packs/{pack_id}",
    response_model=AuthorityPackResult,
)
async def get_authority_pack_endpoint(
    pack_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a previously generated authority pack."""
    result = await get_authority_pack(db, pack_id)
    if not result:
        raise HTTPException(status_code=404, detail="Authority pack not found")
    return result
