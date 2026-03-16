"""Anomaly Detection API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.user import User
from app.schemas.anomaly_detection import Anomaly, AnomalyReport, AnomalyTrend
from app.services.anomaly_detection_service import (
    detect_anomalies,
    detect_portfolio_anomalies,
    get_anomaly_trend,
    get_critical_anomalies,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/anomalies",
    response_model=AnomalyReport,
)
async def get_building_anomalies(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalies for a specific building."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return await detect_anomalies(db, building_id)


@router.get(
    "/portfolio/anomalies",
    response_model=list[AnomalyReport],
)
async def portfolio_anomalies(
    org_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalies across the portfolio."""
    return await detect_portfolio_anomalies(db, org_id=org_id, limit=limit)


@router.get(
    "/buildings/{building_id}/anomalies/trend",
    response_model=AnomalyTrend,
)
async def building_anomaly_trend(
    building_id: uuid.UUID,
    months: int = Query(12, ge=1, le=120),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return anomaly trend for a building over past N months."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return await get_anomaly_trend(db, building_id, months=months)


@router.get(
    "/portfolio/anomalies/critical",
    response_model=list[Anomaly],
)
async def portfolio_critical_anomalies(
    org_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Return critical anomalies across the portfolio."""
    return await get_critical_anomalies(db, org_id=org_id)
