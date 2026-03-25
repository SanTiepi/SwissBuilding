"""BatiConnect — Demo Scenario, Pilot Scorecard, ROI, and Case Study Template API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models.case_study_template import CaseStudyTemplate
from app.models.demo_scenario import DemoScenario
from app.models.pilot_scorecard import PilotMetric, PilotScorecard
from app.models.user import User
from app.schemas.demo_pilot import (
    CaseStudyTemplateRead,
    DemoScenarioRead,
    DemoScenarioWithRunbook,
    PilotMetricCreate,
    PilotMetricRead,
    PilotScorecardRead,
    PilotScorecardWithMetrics,
)
from app.schemas.roi import ROIReport
from app.services.roi_calculator_service import calculate_building_roi

router = APIRouter()


# ---- Demo Scenarios ----


@router.get("/demo/scenarios", response_model=list[DemoScenarioRead])
async def list_demo_scenarios(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all active demo scenarios."""
    stmt = select(DemoScenario).where(DemoScenario.is_active.is_(True)).order_by(DemoScenario.created_at)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/demo/scenarios/{code}/runbook", response_model=DemoScenarioWithRunbook)
async def get_demo_scenario_runbook(
    code: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a demo scenario with its runbook steps."""
    stmt = (
        select(DemoScenario).options(selectinload(DemoScenario.runbook_steps)).where(DemoScenario.scenario_code == code)
    )
    result = await db.execute(stmt)
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Demo scenario not found")
    return scenario


# ---- Pilot Scorecards ----


@router.get("/pilots", response_model=list[PilotScorecardRead])
async def list_pilots(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all pilot scorecards."""
    stmt = select(PilotScorecard).order_by(PilotScorecard.start_date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/pilots/{code}/scorecard", response_model=PilotScorecardWithMetrics)
async def get_pilot_scorecard(
    code: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a pilot scorecard with all its metrics."""
    stmt = select(PilotScorecard).options(selectinload(PilotScorecard.metrics)).where(PilotScorecard.pilot_code == code)
    result = await db.execute(stmt)
    scorecard = result.scalar_one_or_none()
    if not scorecard:
        raise HTTPException(status_code=404, detail="Pilot scorecard not found")
    return scorecard


@router.post("/pilots/{code}/metrics", response_model=PilotMetricRead, status_code=201)
async def add_pilot_metric(
    code: str,
    payload: PilotMetricCreate,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Add a metric measurement to a pilot scorecard."""
    stmt = select(PilotScorecard).where(PilotScorecard.pilot_code == code)
    result = await db.execute(stmt)
    scorecard = result.scalar_one_or_none()
    if not scorecard:
        raise HTTPException(status_code=404, detail="Pilot scorecard not found")

    metric = PilotMetric(
        scorecard_id=scorecard.id,
        dimension=payload.dimension,
        target_value=payload.target_value,
        current_value=payload.current_value,
        evidence_source=payload.evidence_source,
        notes=payload.notes,
        measured_at=payload.measured_at,
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


# ---- ROI ----


@router.get("/buildings/{building_id}/roi", response_model=ROIReport)
async def get_building_roi(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Calculate ROI for a building based on workflow events."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return await calculate_building_roi(db, building_id)


# ---- Case Study Templates ----


@router.get("/case-study-templates", response_model=list[CaseStudyTemplateRead])
async def list_case_study_templates(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all active case study templates."""
    stmt = select(CaseStudyTemplate).where(CaseStudyTemplate.is_active.is_(True)).order_by(CaseStudyTemplate.created_at)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/case-study-templates/{code}", response_model=CaseStudyTemplateRead)
async def get_case_study_template(
    code: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific case study template by code."""
    stmt = select(CaseStudyTemplate).where(CaseStudyTemplate.template_code == code)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Case study template not found")
    return template
