"""BatiConnect — Demo Path and Pilot Scorecard computed API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.demo_path import DemoScenarioResult
from app.schemas.pilot_scorecard import PilotScorecardResult

router = APIRouter()


@router.get("/demo/paths", response_model=list[DemoScenarioResult])
async def list_demo_paths(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List available guided demo scenarios with step counts."""
    from app.services.demo_path_service import list_demo_scenarios

    scenarios = await list_demo_scenarios(db)
    # Return without steps for the list view
    for s in scenarios:
        s.steps = []
    return scenarios


@router.get("/demo/paths/{scenario_type}", response_model=DemoScenarioResult)
async def get_demo_path(
    scenario_type: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific demo scenario with all steps."""
    from app.services.demo_path_service import get_demo_scenario

    result = await get_demo_scenario(db, scenario_type)
    if result is None:
        raise HTTPException(status_code=404, detail="Demo scenario not found")
    return result


@router.get("/organizations/{org_id}/pilot-scorecard", response_model=PilotScorecardResult)
async def get_org_pilot_scorecard(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compute pilot scorecard metrics for an organization."""
    from app.services.pilot_scorecard_service import compute_pilot_scorecard

    return await compute_pilot_scorecard(db, org_id)
