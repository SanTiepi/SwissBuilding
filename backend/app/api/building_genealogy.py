"""Building Genealogy API routes — transformations, ownership, historical claims, timeline."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_genealogy import (
    BuildingGenealogyResponse,
    DeclaredVsObservedResponse,
    GenealogyTimeline,
    HistoricalClaimCreate,
    HistoricalClaimRead,
    OwnershipEpisodeCreate,
    OwnershipEpisodeRead,
    TransformationEpisodeCreate,
    TransformationEpisodeRead,
)
from app.services import genealogy_service

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Full genealogy
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/genealogy",
    response_model=BuildingGenealogyResponse,
    tags=["Building Genealogy"],
)
async def get_building_genealogy(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get complete building genealogy: transformations, ownership, historical claims."""
    await _get_building_or_404(db, building_id)
    return await genealogy_service.get_building_genealogy(db, building_id)


# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/genealogy/transformations",
    response_model=TransformationEpisodeRead,
    status_code=201,
    tags=["Building Genealogy"],
)
async def add_transformation(
    building_id: UUID,
    data: TransformationEpisodeCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a transformation episode in the building's history."""
    await _get_building_or_404(db, building_id)
    episode = await genealogy_service.add_transformation(db, building_id, data)
    await db.commit()
    await db.refresh(episode)
    return episode


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/genealogy/ownership",
    response_model=OwnershipEpisodeRead,
    status_code=201,
    tags=["Building Genealogy"],
)
async def add_ownership_episode(
    building_id: UUID,
    data: OwnershipEpisodeCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record an ownership episode in the building's history."""
    await _get_building_or_404(db, building_id)
    episode = await genealogy_service.add_ownership_episode(db, building_id, data)
    await db.commit()
    await db.refresh(episode)
    return episode


# ---------------------------------------------------------------------------
# Historical claims
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/genealogy/historical-claims",
    response_model=HistoricalClaimRead,
    status_code=201,
    tags=["Building Genealogy"],
)
async def add_historical_claim(
    building_id: UUID,
    data: HistoricalClaimCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a historical claim about the building."""
    await _get_building_or_404(db, building_id)
    claim = await genealogy_service.add_historical_claim(db, building_id, data)
    await db.commit()
    await db.refresh(claim)
    return claim


# ---------------------------------------------------------------------------
# Unified timeline
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/genealogy/timeline",
    response_model=GenealogyTimeline,
    tags=["Building Genealogy"],
)
async def get_genealogy_timeline(
    building_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Unified chronological timeline: transformations + ownership + claims + events."""
    await _get_building_or_404(db, building_id)
    return await genealogy_service.get_genealogy_timeline(db, building_id, limit=limit)


# ---------------------------------------------------------------------------
# Declared vs Observed
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/genealogy/declared-vs-observed",
    response_model=DeclaredVsObservedResponse,
    tags=["Building Genealogy"],
)
async def compare_declared_vs_observed(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare declared historical claims vs observed state. Flag discrepancies."""
    await _get_building_or_404(db, building_id)
    return await genealogy_service.compare_declared_vs_observed(db, building_id)
