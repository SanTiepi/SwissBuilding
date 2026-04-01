"""BatiConnect — Conformance Check API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.conformance import (
    ConformanceCheckRead,
    ConformanceCheckRequest,
    ConformanceCheckSummary,
    RequirementProfileCreate,
    RequirementProfileRead,
)
from app.services.conformance_service import (
    create_profile,
    get_building_checks,
    get_check_summary,
    list_profiles,
    run_conformance_check,
)

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


@router.get(
    "/conformance/profiles",
    response_model=list[RequirementProfileRead],
)
async def list_profiles_endpoint(
    profile_type: str | None = Query(None, description="Filtrer par type (pack, import, publication, exchange)"),
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Lister les profils d'exigences de conformite."""
    return await list_profiles(db, profile_type=profile_type)


@router.post(
    "/conformance/profiles",
    response_model=RequirementProfileRead,
    status_code=201,
)
async def create_profile_endpoint(
    payload: RequirementProfileCreate,
    current_user: User = Depends(require_permission("buildings", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Creer un profil d'exigences de conformite."""
    data = payload.model_dump(exclude_unset=True)
    profile = await create_profile(db, data)
    await db.commit()
    return profile


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/conformance/check",
    response_model=ConformanceCheckRead,
    status_code=201,
)
async def run_check_endpoint(
    building_id: UUID,
    payload: ConformanceCheckRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Executer une verification de conformite contre un profil d'exigences."""
    await _get_building_or_404(db, building_id)
    try:
        check = await run_conformance_check(
            db,
            building_id=building_id,
            profile_name=payload.profile_name,
            target_type=payload.target_type,
            target_id=payload.target_id,
            checked_by_id=current_user.id,
        )
        await db.commit()
        return check
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get(
    "/buildings/{building_id}/conformance/checks",
    response_model=list[ConformanceCheckRead],
)
async def list_checks_endpoint(
    building_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Lister les verifications de conformite d'un batiment."""
    await _get_building_or_404(db, building_id)
    return await get_building_checks(db, building_id, limit=limit)


@router.get(
    "/buildings/{building_id}/conformance/summary",
    response_model=ConformanceCheckSummary,
)
async def check_summary_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Resume des verifications de conformite d'un batiment."""
    await _get_building_or_404(db, building_id)
    return await get_check_summary(db, building_id)
