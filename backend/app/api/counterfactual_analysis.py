"""Counterfactual analysis API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.counterfactual_analysis import (
    BuildingTimelineAnalysis,
    CounterfactualResult,
    PortfolioStressTest,
    StressTestResult,
)
from app.services.counterfactual_analysis_service import (
    analyze_timeline_alternatives,
    run_counterfactual,
    run_portfolio_stress_test,
    run_stress_test,
)

router = APIRouter()


@router.get(
    "/counterfactual-analysis/buildings/{building_id}/scenario",
    response_model=CounterfactualResult,
)
async def get_counterfactual_scenario(
    building_id: UUID,
    scenario_type: str = Query(default="delayed_action"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Run a counterfactual what-if scenario on a building."""
    try:
        return await run_counterfactual(building_id, scenario_type, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/counterfactual-analysis/buildings/{building_id}/stress-test",
    response_model=StressTestResult,
)
async def get_stress_test(
    building_id: UUID,
    stress_type: str = Query(default="regulatory_tightening"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Run a stress test on a building."""
    try:
        return await run_stress_test(building_id, stress_type, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/counterfactual-analysis/buildings/{building_id}/timeline-alternatives",
    response_model=BuildingTimelineAnalysis,
)
async def get_timeline_alternatives(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate timeline alternatives for building remediation."""
    try:
        return await analyze_timeline_alternatives(building_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/counterfactual-analysis/organizations/{org_id}/stress-test",
    response_model=PortfolioStressTest,
)
async def get_portfolio_stress_test(
    org_id: UUID,
    stress_type: str = Query(default="regulatory_tightening"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Run a stress test across all buildings in an organization."""
    try:
        return await run_portfolio_stress_test(org_id, stress_type, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
