"""Pack impact simulation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.pack_impact import (
    AffectedPack,
    PackImpactSimulateRequest,
    PackImpactSimulation,
)
from app.services.pack_impact_service import get_stale_packs, simulate_pack_impact

router = APIRouter()


@router.get(
    "/buildings/{building_id}/pack-impact",
    response_model=PackImpactSimulation,
)
async def get_pack_impact_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate impact of all planned interventions on evidence packs."""
    result = await simulate_pack_impact(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.post(
    "/buildings/{building_id}/pack-impact/simulate",
    response_model=PackImpactSimulation,
)
async def simulate_pack_impact_endpoint(
    building_id: UUID,
    body: PackImpactSimulateRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate impact of specific interventions on evidence packs."""
    result = await simulate_pack_impact(db, building_id, intervention_ids=body.intervention_ids)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/stale-packs",
    response_model=list[AffectedPack],
)
async def get_stale_packs_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get currently stale evidence packs for a building."""
    return await get_stale_packs(db, building_id)
