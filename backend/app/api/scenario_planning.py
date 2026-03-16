"""Scenario planning API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.scenario_planning import (
    CompareRequest,
    CompareResponse,
    OptimalRequest,
    OptimalScenarioResponse,
    ScenarioCreateRequest,
    ScenarioResult,
    SensitivityRequest,
    SensitivityResponse,
)
from app.services.scenario_planning_service import (
    compare_scenarios,
    create_scenario,
    find_optimal_scenario,
    get_scenario_sensitivity,
)

router = APIRouter()


@router.post(
    "/buildings/{building_id}/scenarios",
    response_model=ScenarioResult,
)
async def post_create_scenario(
    building_id: UUID,
    body: ScenarioCreateRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Create and evaluate a what-if scenario for a building."""
    try:
        return await create_scenario(db, building_id, body.name, body.interventions)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/buildings/{building_id}/scenarios/compare",
    response_model=CompareResponse,
)
async def post_compare_scenarios(
    building_id: UUID,
    body: CompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare up to 5 scenarios side-by-side."""
    try:
        return await compare_scenarios(db, building_id, body.scenarios)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/buildings/{building_id}/scenarios/optimal",
    response_model=OptimalScenarioResponse,
)
async def post_optimal_scenario(
    building_id: UUID,
    body: OptimalRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate the best scenario within budget and time constraints."""
    try:
        return await find_optimal_scenario(db, building_id, body.budget_limit_chf, body.time_limit_months)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/buildings/{building_id}/scenarios/sensitivity",
    response_model=SensitivityResponse,
)
async def post_sensitivity(
    building_id: UUID,
    body: SensitivityRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Run sensitivity analysis on a scenario."""
    try:
        return await get_scenario_sensitivity(db, building_id, body.scenario)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
