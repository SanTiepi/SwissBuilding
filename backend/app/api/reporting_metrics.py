"""Reporting metrics API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.reporting_metrics import (
    BenchmarkComparison,
    KPIDashboard,
    OperationalMetrics,
    PeriodicReport,
)
from app.services.reporting_metrics_service import (
    generate_periodic_report,
    get_benchmark_comparison,
    get_kpi_dashboard,
    get_operational_metrics,
)

router = APIRouter()


@router.get(
    "/organizations/{org_id}/kpi-dashboard",
    response_model=KPIDashboard,
)
async def kpi_dashboard(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get key performance indicators for an organization with trend data."""
    try:
        return await get_kpi_dashboard(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/operational-metrics",
    response_model=OperationalMetrics,
)
async def operational_metrics(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get operational statistics for an organization."""
    try:
        return await get_operational_metrics(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/periodic-report",
    response_model=PeriodicReport,
)
async def periodic_report(
    org_id: UUID,
    period: str = Query("monthly", pattern="^(monthly|quarterly|annual)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured periodic report for an organization."""
    try:
        return await generate_periodic_report(db, org_id, period)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/benchmark",
    response_model=BenchmarkComparison,
)
async def benchmark_comparison(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare organization metrics against system-wide averages."""
    try:
        return await get_benchmark_comparison(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
