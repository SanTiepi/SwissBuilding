"""Adoption Loops — Package presets API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.package_preset import ExternalViewerProfileRead, PresetPreview, PresetRead
from app.services.package_preset_service import (
    get_preset,
    list_presets,
    list_viewer_profiles,
    preview_package,
)

router = APIRouter()


@router.get(
    "/package-presets",
    response_model=list[PresetRead],
)
async def list_presets_endpoint(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_presets(db)


@router.get(
    "/package-presets/{preset_code}",
    response_model=PresetRead,
)
async def get_preset_endpoint(
    preset_code: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    preset = await get_preset(db, preset_code)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.get(
    "/buildings/{building_id}/package-preview/{preset_code}",
    response_model=PresetPreview,
)
async def preview_package_endpoint(
    building_id: UUID,
    preset_code: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    result = await preview_package(db, building_id, preset_code)
    if not result:
        raise HTTPException(status_code=404, detail="Preset not found")
    return result


@router.get(
    "/external-viewer-profiles",
    response_model=list[ExternalViewerProfileRead],
)
async def list_viewer_profiles_endpoint(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    return await list_viewer_profiles(db)
