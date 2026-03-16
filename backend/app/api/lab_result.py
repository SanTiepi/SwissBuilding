"""Lab Result Analysis API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.user import User
from app.schemas.lab_result import (
    LabResultAnalysis,
    LabSummaryReport,
    ResultAnomalyReport,
    ResultTrends,
)
from app.services.lab_result_service import (
    analyze_lab_results,
    detect_result_anomalies,
    generate_lab_summary_report,
    get_result_trends,
)

router = APIRouter()


async def _verify_building(db: AsyncSession, building_id: uuid.UUID) -> None:
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Building not found")


@router.get(
    "/buildings/{building_id}/lab-results/analysis",
    response_model=LabResultAnalysis,
)
async def get_lab_result_analysis(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Consolidated lab result analysis for a building."""
    await _verify_building(db, building_id)
    return await analyze_lab_results(db, building_id)


@router.get(
    "/buildings/{building_id}/lab-results/anomalies",
    response_model=ResultAnomalyReport,
)
async def get_lab_result_anomalies(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalies in lab results for a building."""
    await _verify_building(db, building_id)
    return await detect_result_anomalies(db, building_id)


@router.get(
    "/buildings/{building_id}/lab-results/trends",
    response_model=ResultTrends,
)
async def get_lab_result_trends(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Temporal trend analysis of lab results for a building."""
    await _verify_building(db, building_id)
    return await get_result_trends(db, building_id)


@router.get(
    "/buildings/{building_id}/lab-results/summary",
    response_model=LabSummaryReport,
)
async def get_lab_summary_report(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Structured summary report of lab results for a building."""
    await _verify_building(db, building_id)
    return await generate_lab_summary_report(db, building_id)
