"""Climate exposure and opportunity window API routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.climate_exposure import (
    BestTimingResponse,
    ClimateExposureProfileRead,
    ClimateExposureRefreshResponse,
    OpportunityDetectResponse,
    OpportunityWindowRead,
    OpportunityWindowsResponse,
)
from app.services.climate_opportunity_service import (
    build_exposure_profile,
    detect_opportunity_windows,
    get_active_windows,
    get_best_timing,
    get_exposure_profile,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/climate-exposure",
    response_model=ClimateExposureProfileRead | None,
    tags=["Climate Exposure"],
)
async def get_climate_exposure(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get the climate exposure profile for a building."""
    profile = await get_exposure_profile(db, building_id)
    if profile is None:
        return None
    return profile


@router.post(
    "/buildings/{building_id}/climate-exposure/refresh",
    response_model=ClimateExposureRefreshResponse,
    tags=["Climate Exposure"],
)
async def refresh_climate_exposure(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Build or refresh the climate exposure profile from geo.admin data."""
    try:
        profile = await build_exposure_profile(db, building_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    layers_merged = len(profile.data_sources) if profile.data_sources else 0
    return ClimateExposureRefreshResponse(
        profile=ClimateExposureProfileRead.model_validate(profile),
        layers_merged=layers_merged,
        message=f"Profil d'exposition mis a jour ({layers_merged} couches)",
    )


@router.get(
    "/buildings/{building_id}/opportunity-windows",
    response_model=OpportunityWindowsResponse,
    tags=["Climate Exposure"],
)
async def get_opportunity_windows(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get active opportunity windows for a building."""
    windows = await get_active_windows(db, building_id)
    return OpportunityWindowsResponse(
        windows=[OpportunityWindowRead.model_validate(w) for w in windows],
        total=len(windows),
        active_count=len(windows),
    )


@router.post(
    "/buildings/{building_id}/opportunity-windows/detect",
    response_model=OpportunityDetectResponse,
    tags=["Climate Exposure"],
)
async def detect_windows(
    building_id: UUID,
    case_id: UUID | None = None,
    horizon_days: int = 365,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Detect new opportunity windows for a building."""
    try:
        created = await detect_opportunity_windows(
            db,
            building_id,
            case_id=case_id,
            horizon_days=horizon_days,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    all_active = await get_active_windows(db, building_id)
    return OpportunityDetectResponse(
        detected=len(all_active),
        new=len(created),
        expired=0,
        windows=[OpportunityWindowRead.model_validate(w) for w in all_active],
    )


@router.get(
    "/buildings/{building_id}/best-timing/{work_type}",
    response_model=BestTimingResponse,
    tags=["Climate Exposure"],
)
async def best_timing_for_work(
    building_id: UUID,
    work_type: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Recommend best timing for a specific work type."""
    result = await get_best_timing(db, building_id, work_type)
    matching_windows = result.get("matching_windows", [])
    return BestTimingResponse(
        work_type=result["work_type"],
        recommended_period=result.get("recommended_period"),
        recommended_start=result.get("recommended_start"),
        recommended_end=result.get("recommended_end"),
        reason=result.get("reason"),
        matching_windows=[OpportunityWindowRead.model_validate(w) for w in matching_windows],
        warnings=result.get("warnings", []),
    )
