"""Renovation readiness assessment API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.renovation_readiness_service import (
    assess_readiness,
    generate_readiness_pack,
    list_renovation_options,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get("/buildings/{building_id}/renovation-readiness/{work_type}")
async def assess_renovation_readiness(
    building_id: UUID,
    work_type: str,
    current_user: User = Depends(require_permission("readiness", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get renovation readiness assessment for a specific work type."""
    await _get_building_or_404(db, building_id)
    result = await assess_readiness(db, building_id, work_type, org_id=current_user.organization_id)
    if result.get("error") == "unknown_work_type":
        raise HTTPException(status_code=400, detail=result["detail"])
    return result


@router.post("/buildings/{building_id}/renovation-readiness/{work_type}/pack")
async def generate_renovation_pack(
    building_id: UUID,
    work_type: str,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Generate the renovation readiness pack."""
    await _get_building_or_404(db, building_id)
    result = await generate_readiness_pack(
        db,
        building_id,
        work_type,
        org_id=current_user.organization_id,
        created_by_id=current_user.id,
    )
    if result.get("error") == "unknown_work_type":
        raise HTTPException(status_code=400, detail=result.get("detail", "Unknown work type"))
    if result.get("error") == "pack_not_ready":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Pack cannot be generated yet",
                "blockers": result.get("pack_blockers", []),
            },
        )
    return result


@router.get("/buildings/{building_id}/renovation-readiness")
async def list_renovation_options_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("readiness", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List available renovation types with quick readiness indicator for each."""
    await _get_building_or_404(db, building_id)
    return await list_renovation_options(db, building_id)
