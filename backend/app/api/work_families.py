"""BatiConnect — Work-Family Trade Matrix API routes.

Exposes the work-family matrix: list all families, get details, compute
coverage for a building, and resolve requirements for a case.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.work_family import (
    BuildingWorkFamilyCoverage,
    CaseWorkFamilyRequirements,
    WorkFamilyRead,
)
from app.services import work_family_service

router = APIRouter()


@router.get(
    "/work-families",
    response_model=list[WorkFamilyRead],
)
async def list_work_families(
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """List all work families with their full definitions."""
    return await work_family_service.get_all_families()


@router.get(
    "/work-families/{name}",
    response_model=WorkFamilyRead,
)
async def get_work_family(
    name: str,
    current_user: User = Depends(require_permission("buildings", "read")),
):
    """Get a single work family definition by name."""
    result = await work_family_service.get_work_family(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Work family '{name}' not found")
    return result


@router.get(
    "/buildings/{building_id}/work-family-coverage",
    response_model=BuildingWorkFamilyCoverage,
)
async def get_building_work_family_coverage(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """For each work family, show what the building already has vs what's missing."""
    result = await work_family_service.get_coverage_for_building(db, building_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get(
    "/cases/{case_id}/work-family-requirements",
    response_model=CaseWorkFamilyRequirements,
)
async def get_case_work_family_requirements(
    case_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Given a BuildingCase, determine all work-family requirements."""
    result = await work_family_service.get_requirements_for_case(db, case_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
