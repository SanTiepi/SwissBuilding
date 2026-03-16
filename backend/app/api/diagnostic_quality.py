"""Diagnostic quality assessment API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.diagnostic_quality import (
    DiagnosticBenchmarks,
    DiagnosticDeficiencyResult,
    DiagnosticianComparisonResult,
    DiagnosticQualityScore,
)
from app.services.diagnostic_quality_service import (
    compare_diagnostician_performance,
    detect_diagnostic_deficiencies,
    evaluate_diagnostic_quality,
    get_diagnostic_benchmarks,
)

router = APIRouter()


@router.get(
    "/diagnostics/{diagnostic_id}/quality",
    response_model=DiagnosticQualityScore,
)
async def get_diagnostic_quality(
    diagnostic_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate quality score for a diagnostic."""
    result = await evaluate_diagnostic_quality(db, diagnostic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    return result


@router.get(
    "/organizations/{org_id}/diagnostician-performance",
    response_model=DiagnosticianComparisonResult,
)
async def get_diagnostician_performance(
    org_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare diagnostician performance within an organization."""
    result = await compare_diagnostician_performance(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result


@router.get(
    "/diagnostics/{diagnostic_id}/deficiencies",
    response_model=DiagnosticDeficiencyResult,
)
async def get_diagnostic_deficiencies(
    diagnostic_id: UUID,
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Detect deficiencies in a diagnostic with fix actions."""
    result = await detect_diagnostic_deficiencies(db, diagnostic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagnostic not found")
    return result


@router.get(
    "/diagnostic-benchmarks",
    response_model=DiagnosticBenchmarks,
)
async def get_benchmarks(
    current_user: User = Depends(require_permission("diagnostics", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide diagnostic quality benchmarks."""
    return await get_diagnostic_benchmarks(db)
