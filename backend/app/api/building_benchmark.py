"""Building benchmark API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_benchmark import (
    BenchmarkCompareRequest,
    BenchmarkComparison,
    BuildingBenchmark,
    CantonBenchmark,
    PeerGroup,
)
from app.services.building_benchmark_service import (
    benchmark_building,
    compare_buildings_benchmark,
    get_canton_benchmarks,
    get_peer_group,
)

router = APIRouter()


@router.get("/buildings/{building_id}/benchmark", response_model=BuildingBenchmark)
async def get_building_benchmark(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get peer-based benchmark for a single building."""
    try:
        result = await benchmark_building(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.post("/buildings/benchmark/compare", response_model=BenchmarkComparison)
async def compare_buildings_benchmark_endpoint(
    body: BenchmarkCompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare benchmarks across multiple buildings."""
    try:
        result = await compare_buildings_benchmark(db, body.building_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.get("/benchmarks/cantons", response_model=list[CantonBenchmark])
async def get_canton_benchmarks_endpoint(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate benchmark statistics per canton."""
    return await get_canton_benchmarks(db)


@router.get("/buildings/{building_id}/peer-group", response_model=PeerGroup)
async def get_building_peer_group(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the peer group for a building."""
    try:
        result = await get_peer_group(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result
