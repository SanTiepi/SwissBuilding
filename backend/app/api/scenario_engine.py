"""BatiConnect — Counterfactual Scenario Engine API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.scenario import (
    ScenarioCompareItem,
    ScenarioCompareRequest,
    ScenarioCompareResponse,
    ScenarioCreate,
    ScenarioEvaluateResponse,
    ScenarioRead,
)
from app.services.scenario_engine import (
    compare_scenarios,
    create_scenario,
    evaluate_scenario,
    generate_standard_scenarios,
    get_building_scenarios,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/counterfactual-scenarios",
    response_model=ScenarioRead,
    status_code=201,
)
async def post_create_scenario(
    building_id: UUID,
    payload: ScenarioCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new counterfactual scenario for a building."""
    try:
        scenario = await create_scenario(
            db,
            building_id=building_id,
            scenario_type=payload.scenario_type,
            title=payload.title,
            assumptions=payload.assumptions,
            created_by_id=current_user.id,
            org_id=current_user.organization_id,
            case_id=payload.case_id,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return scenario


@router.get(
    "/buildings/{building_id}/counterfactual-scenarios",
    response_model=list[ScenarioRead],
)
async def get_scenarios(
    building_id: UUID,
    status: str | None = Query(default=None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all counterfactual scenarios for a building."""
    return await get_building_scenarios(db, building_id, status=status)


@router.post(
    "/counterfactual-scenarios/{scenario_id}/evaluate",
    response_model=ScenarioEvaluateResponse,
)
async def post_evaluate_scenario(
    scenario_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate a scenario by projecting outcomes from canonical truth."""
    try:
        scenario, summary = await evaluate_scenario(db, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return ScenarioEvaluateResponse(
        scenario=ScenarioRead.model_validate(scenario),
        evaluation_summary=summary,
    )


@router.post(
    "/buildings/{building_id}/counterfactual-scenarios/compare",
    response_model=ScenarioCompareResponse,
)
async def post_compare_scenarios(
    building_id: UUID,
    payload: ScenarioCompareRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare multiple counterfactual scenarios side by side."""
    try:
        result = await compare_scenarios(db, building_id, payload.scenario_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return ScenarioCompareResponse(
        building_id=building_id,
        baseline_grade=result["baseline_grade"],
        baseline_cost_chf=result["baseline_cost_chf"],
        scenarios=[ScenarioCompareItem.model_validate(s) for s in result["scenarios"]],
        recommendation=result["recommendation"],
    )


@router.post(
    "/buildings/{building_id}/counterfactual-scenarios/generate-standard",
    response_model=list[ScenarioRead],
    status_code=201,
)
async def post_generate_standard(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate standard counterfactual scenarios for common what-ifs."""
    try:
        scenarios = await generate_standard_scenarios(
            db,
            building_id=building_id,
            created_by_id=current_user.id,
            org_id=current_user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return scenarios
